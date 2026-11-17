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
        records[p.external_id]={**p.payload,'origen':'Registro manual HIDRO' if p.payload.get('_manual') else 'Caracterización EAAB · CSV'}
    from app.services.activity_demand import estimate
    for r in records.values():
        r.update(estimate(r))
    return sorted(records.values(),key=lambda r:r['id_predio_demo'])

async def demand_parcels(db,uid,land_use=None):
    rows=await unified_records(db,uid)
    english={**{v:k for k,v in USES.items()},'Industrial':'Industrial','Oficial':'Official','Multiusuario':'Multiuser','Multiuso':'Multiuser'}
    return [SimpleNamespace(parcel_id=r['id_predio_demo'],land_use=english.get(r['clase_uso'],r['clase_uso']),population=r['numero_habitantes'] or 0,lat=r['lat'],lng=r['lng'],daily90=r['demanda_diaria_90_m3']*1000,daily100=r['demanda_diaria_100_m3']*1000) for r in rows if r['demanda_diaria_90_m3'] is not None and (not land_use or land_use=='All' or english.get(r['clase_uso'])==land_use)]

def daily_for(p, scenario=90):
    return p.daily100 if scenario==100 else p.daily90

def yearly_for(p, scenario=90):
    return daily_for(p,scenario)*365
