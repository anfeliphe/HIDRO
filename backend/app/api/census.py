"""Provisional census import, isolated from demand estimates and legacy parcels."""
import csv
import io
import math
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, constr
from sqlalchemy import Column, Integer, String, JSON, UniqueConstraint, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import Base, get_db
from app.api.deps import get_current_user_id

class CensusRecord(Base):
    __tablename__ = 'census_records'
    __table_args__ = (UniqueConstraint('owner_id', 'external_id'),)
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, nullable=False, index=True)
    external_id = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)

router = APIRouter(prefix='/census', tags=['Censo provisional'])
FIELDS = 'id_predio_demo id_usuario fecha_censo plano zona barrio manzana municipio direccion clase_uso tipo_actividad tipo_punto unidades_habitacionales unidades_no_habitacionales total_unidades numero_familias numero_habitantes tiene_agua horas_servicio tanque_reserva disponibilidad_cajilla clasificacion tiene_medidor lat lng dato_simulado'.split()
NUMBERS = {'unidades_habitacionales':500,'unidades_no_habitacionales':500,'total_unidades':1000,'numero_familias':50,'numero_habitantes':200,'horas_servicio':24}
BOOLEANS = ['tiene_agua','tanque_reserva','disponibilidad_cajilla','tiene_medidor','dato_simulado']

def parse_census(content):
    if not content.strip():
        raise ValueError('El archivo está vacío.')
    reader = csv.DictReader(io.StringIO(content.lstrip('\ufeff')), delimiter=';' if ';' in content.splitlines()[0] else ',')
    if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise ValueError('Encabezados vacíos o duplicados.')
    missing = set(FIELDS)-set(reader.fieldnames)
    if missing:
        raise ValueError('Faltan columnas del modelo: '+', '.join(sorted(missing)))
    rows, seen = [], set()
    for line, raw in enumerate(reader,2):
        try:
            if None in raw: raise ValueError('Columnas adicionales sin encabezado.')
            r = {k:(raw.get(k) or '').strip() for k in FIELDS}
            for k in ['id_predio_demo','id_usuario','fecha_censo','barrio','municipio','clase_uso','lat','lng']:
                if not r[k]: raise ValueError(f'{k} es obligatorio.')
            if len(r['id_predio_demo'])>100: raise ValueError('Identificador demasiado largo.')
            if r['id_predio_demo'] in seen: raise ValueError('Predio duplicado en el archivo.')
            seen.add(r['id_predio_demo'])
            date.fromisoformat(r['fecha_censo'])
            if r['clase_uso'] not in ['Residencial','Comercial','Industrial','Oficial','Multiusuario']: raise ValueError('Clase de uso no reconocida.')
            for k,limit in NUMBERS.items():
                r[k] = float(r[k]) if r[k] else None
                if r[k] is not None and (not math.isfinite(r[k]) or not 0<=r[k]<=limit or (k!='horas_servicio' and not r[k].is_integer())): raise ValueError(f'{k} fuera de rango o no válido.')
            for k in BOOLEANS:
                v=r[k].lower()
                if v not in ['sí','si','no']: raise ValueError(f'{k} debe ser Sí o No.')
                r[k]=v in ['sí','si']
            for k,limit in [('lat',90),('lng',180)]:
                r[k]=float(r[k])
                if not math.isfinite(r[k]) or not -limit<=r[k]<=limit: raise ValueError(f'{k} no válida.')
            if not r['tiene_agua'] and r['horas_servicio'] is not None: raise ValueError('Sin agua: horas_servicio debe quedar vacío.')
            if r['numero_habitantes'] is not None and r['numero_familias'] is not None and r['numero_habitantes']<r['numero_familias']: raise ValueError('Habitantes menores que familias.')
            a,b,t=(r[k] for k in ['unidades_habitacionales','unidades_no_habitacionales','total_unidades'])
            if all(v is not None for v in (a,b,t)) and a+b!=t: raise ValueError('El total de unidades no coincide.')
            rows.append(r)
            if len(rows)>5000: raise ValueError('Máximo 5000 predios por archivo.')
        except (ValueError,TypeError) as e:
            raise ValueError(f'Fila {line}: {e}') from e
    if not rows: raise ValueError('El archivo no contiene registros.')
    return rows

class ImportBody(BaseModel):
    content: constr(max_length=2_000_000)
    preview: bool = True

@router.get('/unified')
async def unified_census(db:AsyncSession=Depends(get_db), uid:int=Depends(get_current_user_id)):
    from app.services.hidro_data import unified_records
    return await unified_records(db,uid)

@router.get('')
async def list_census(db:AsyncSession=Depends(get_db), uid:int=Depends(get_current_user_id)):
    result=await db.execute(select(CensusRecord).where(CensusRecord.owner_id==uid).order_by(CensusRecord.external_id))
    return [r.payload for r in result.scalars()]

@router.post('/import')
async def import_census(body:ImportBody, db:AsyncSession=Depends(get_db), uid:int=Depends(get_current_user_id)):
    try: rows=parse_census(body.content)
    except (ValueError,IndexError,csv.Error) as e: raise HTTPException(400,str(e))
    existing={r.external_id:r for r in (await db.execute(select(CensusRecord).where(CensusRecord.owner_id==uid))).scalars()}
    updated=sum(r['id_predio_demo'] in existing for r in rows)
    if not body.preview:
        for r in rows:
            key=r['id_predio_demo']
            if key in existing: existing[key].payload=r
            else: db.add(CensusRecord(owner_id=uid,external_id=key,payload=r))
        await db.commit()
    return {'total':len(rows),'inserted':len(rows)-updated,'updated':updated,'simulated':sum(r['dato_simulado'] for r in rows),'preview':body.preview}


@router.delete('/records/{external_id}')
async def delete_census_record(external_id: str, db: AsyncSession = Depends(get_db),
                               user_id: int = Depends(get_current_user_id)):
    record = (await db.execute(select(CensusRecord).where(
        CensusRecord.owner_id == user_id, CensusRecord.external_id == external_id
    ))).scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=404, detail='No se encontró el predio importado')
    await db.delete(record)
    await db.commit()
    return {'message': 'Registro importado eliminado.'}


class ManualRecordBody(BaseModel):
    record: dict


def validate_manual_record(raw):
    """Preserve missing values; do not turn unreported counts or booleans into zero/no."""
    r={key:raw.get(key) for key in FIELDS}
    for key in set(FIELDS)-set(NUMBERS)-set(BOOLEANS)-{'lat','lng'}:
        val=r[key]
        if val is not None and not isinstance(val,str):
            raise ValueError(f'{key}: se esperaba texto.')
        r[key]=(val or '').strip() or None
        if r[key] and len(r[key])>500:raise ValueError(f'{key}: máximo 500 caracteres.')
    if not r['id_predio_demo'] or len(r['id_predio_demo'])>100:
        raise ValueError('El identificador es obligatorio y admite hasta 100 caracteres.')
    if r['clase_uso'] not in ['Residencial','Comercial','Mixto','Industrial','Oficial','Multiusuario']:
        raise ValueError('Selecciona un uso del predio válido.')
    if r['fecha_censo']:
        try:date.fromisoformat(r['fecha_censo'])
        except ValueError:raise ValueError('La fecha del censo no es válida.')
    limits={**NUMBERS,'numero_habitantes':10000}
    for key,limit in limits.items():
        val=r[key]
        if val is None or val=='':r[key]=None;continue
        if isinstance(val,bool):raise ValueError(f'{key}: ingresa un número.')
        try:val=float(val)
        except (ValueError,TypeError):raise ValueError(f'{key}: ingresa un número.')
        if not math.isfinite(val) or not 0<=val<=limit or (key!='horas_servicio' and not val.is_integer()):
            raise ValueError(f'{key}: valor fuera de rango (0–{limit}).')
        r[key]=val if key=='horas_servicio' else int(val)
    for key in BOOLEANS:
        if r[key] is not None and not isinstance(r[key],bool):raise ValueError(f'{key}: selecciona Sí, No o Sin información.')
    for key,limit in [('lat',90),('lng',180)]:
        val=r[key]
        if val is None or val=='' or isinstance(val,bool):raise ValueError('La latitud y longitud son obligatorias.')
        try:val=float(val)
        except (ValueError,TypeError):raise ValueError('La latitud y longitud deben ser numéricas.')
        if not math.isfinite(val) or not -limit<=val<=limit:raise ValueError(f'{key}: coordenada fuera de rango.')
        r[key]=val
    if r['tiene_agua'] is not True and r['horas_servicio'] is not None:
        raise ValueError('Informa las horas de suministro solo cuando recibe agua de red.')
    a,b,t=(r[k] for k in ['unidades_habitacionales','unidades_no_habitacionales','total_unidades'])
    if all(v is not None for v in (a,b,t)) and a+b!=t:raise ValueError('El total de unidades debe ser la suma de las unidades de vivienda y no residenciales.')
    if r['numero_habitantes'] is not None and r['numero_familias'] is not None and r['numero_habitantes']<r['numero_familias']:
        raise ValueError('El número de habitantes no puede ser menor que el de familias.')
    return r

async def save_manual_record(body,db,uid,external_id=None):
    from app.models.parcel import Parcel
    from sqlalchemy.exc import IntegrityError
    try:r=validate_manual_record(body.record)
    except ValueError as e:raise HTTPException(400,str(e))
    key=r['id_predio_demo']
    if external_id is not None and key!=external_id:raise HTTPException(400,'No se puede cambiar el identificador al editar.')
    current=(await db.execute(select(CensusRecord).where(CensusRecord.owner_id==uid,CensusRecord.external_id==key))).scalar_one_or_none()
    legacy=(await db.execute(select(Parcel).where(Parcel.parcel_id==key))).scalar_one_or_none()
    if external_id is None and (current is not None or legacy is not None):raise HTTPException(409,'Ya existe un predio con ese identificador. Utiliza Editar.')
    if external_id is not None and current is None and legacy is None:raise HTTPException(404,'No se encontró el predio para editar.')
    # Server-owned metadata keeps historical demand coefficients without exposing them as editable inputs.
    r['_manual']=True
    r['_historic_coefficients']=bool(current.payload.get('_historic_coefficients')) if current is not None else legacy is not None
    if current is not None:current.payload=r
    else:db.add(CensusRecord(owner_id=uid,external_id=key,payload=r))
    try:await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409,'El predio ya existe. Actualiza la lista antes de continuar.')
    return {'message':'Predio guardado.','id_predio_demo':key}

@router.post('/records',status_code=201)
async def create_manual_record(body:ManualRecordBody,db:AsyncSession=Depends(get_db),uid:int=Depends(get_current_user_id)):
    return await save_manual_record(body,db,uid)

@router.put('/records/{external_id}')
async def update_manual_record(external_id:str,body:ManualRecordBody,db:AsyncSession=Depends(get_db),uid:int=Depends(get_current_user_id)):
    return await save_manual_record(body,db,uid,external_id)
