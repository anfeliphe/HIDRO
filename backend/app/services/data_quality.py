"""Deterministic duplicate checks scoped to the caller's unified dataset."""
import hashlib
import json
import re
from app.services.activity_demand import norm

def key(value):
    return re.sub(r'\s+','',norm(value))

def address(r):
    text=norm(r.get('direccion'))
    for a,b in [('carrera','kr'),('cra','kr'),('calle','cl'),('avenida','av')]:
        text=re.sub(r'\b'+a+r'\b',b,text)
    return re.sub(r'[^a-z0-9]','',text)

def check_duplicates(rows, existing):
    warnings=[];seen={};by_id={key(r['id_predio_demo']):r for r in existing}
    by_address={};by_coords={}
    def index(r):
        addr=address(r)
        if addr:by_address.setdefault((key(r.get('municipio')),addr),[]).append(r)
        by_coords.setdefault((round(r['lat'],5),round(r['lng'],5)),[]).append(r)
    for r in existing:index(r)
    for n,r in enumerate(rows,1):
        pid=r['id_predio_demo'];k=key(pid)
        if k in seen:raise ValueError(f'Registro {n}: identificador duplicado {pid}; coincide con {seen[k]}.')
        seen[k]=pid
        old=by_id.get(k)
        if old and old['id_predio_demo']!=pid:raise ValueError(f'{pid}: coincide con el identificador existente {old["id_predio_demo"]} al ignorar espacios y mayúsculas. Utiliza el identificador existente.')
        candidates={}
        addr=address(r)
        for other in by_address.get((key(r.get('municipio')),addr),[]) if addr else []:
            candidates.setdefault(other['id_predio_demo'],[]).append('misma dirección y municipio')
        for other in by_coords.get((round(r['lat'],5),round(r['lng'],5)),[]):
            candidates.setdefault(other['id_predio_demo'],[]).append('coordenadas coincidentes a 5 decimales')
        for other,reasons in candidates.items():
            if other!=pid:warnings.append(f'{pid} y {other}: posible duplicado ({", ".join(reasons)}). Verifica si son unidades distintas.')
        index(r)
    return list(dict.fromkeys(warnings))

def review_token(rows, existing):
    # Captures data and snapshot; a changed dataset requires a new review.
    stable=sorted(existing,key=lambda r:r['id_predio_demo'])
    return hashlib.sha256(json.dumps([rows,stable],sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest()
