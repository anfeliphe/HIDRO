"""One HIDRO read model for historic parcels and survey imports."""
from types import SimpleNamespace
from sqlalchemy import select
from app.models.parcel import Parcel

USES={'Residential':'Residencial','Commercial':'Comercial','Mixed-use':'Mixto'}

async def unified_records(db, uid):
    from app.api.census import CensusRecord, FIELDS
    legacy=(await db.execute(select(Parcel).order_by(Parcel.parcel_id))).scalars().all()
    surveys=(await db.execute(select(CensusRecord).where(CensusRecord.owner_id==uid))).scalars().all()
    records={}
    for p in legacy:
        r={k:None for k in FIELDS}
        r.update(id_predio_demo=p.parcel_id,clase_uso=USES.get(p.land_use,p.land_use),numero_habitantes=p.population,lat=p.lat,lng=p.lng,barrio='Sin sector informado',origen='HIDRO existente')
        records[p.parcel_id]=r
    for p in surveys:
        records[p.external_id]={**p.payload,'origen':'Caracterización EAAB · CSV'}
    for r in records.values():
        factors={'Residencial':1.0}
        if r['origen']=='HIDRO existente':factors.update({'Comercial':1.2,'Mixto':1.1})
        k=factors.get(r['clase_uso']);pop=r['numero_habitantes']
        r['coeficiente_demanda']=k
        r['demanda_diaria_90_m3']=None if k is None or pop is None else pop*.09*k
        r['demanda_diaria_100_m3']=None if k is None or pop is None else pop*.1*k
        r['motivo_sin_demanda']='' if r['demanda_diaria_90_m3'] is not None else ('Sin dato de habitantes' if pop is None else 'Uso pendiente de metodología de demanda')
    return sorted(records.values(),key=lambda r:r['id_predio_demo'])

async def demand_parcels(db,uid,land_use=None):
    rows=await unified_records(db,uid);english={v:k for k,v in USES.items()}
    return [SimpleNamespace(parcel_id=r['id_predio_demo'],land_use=english[r['clase_uso']],population=r['numero_habitantes'],lat=r['lat'],lng=r['lng']) for r in rows if r['demanda_diaria_90_m3'] is not None and (not land_use or land_use=='All' or english.get(r['clase_uso'])==land_use)]
