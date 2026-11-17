"""Versioned planning assumptions, NOT EAAB tariffs or measured consumption."""
import math
import unicodedata
VERSION = 'HIDRO-usos-2026-11-v1'
EPA = 'https://www.epa.gov/system/files/documents/2023-11/ws-commercial-bmp-watersenseatwork_section5.4_vehiclewashes.pdf'
DOE = 'https://www.energy.gov/cmei/femp/estimating-methods-determining-end-use-water-consumption'
# id, category, label, liters/unit, unit, default quantity, operating days/year
DEFINITIONS = [
 ('vivienda','Residencial','Vivienda',90,'habitantes',4,365),
 ('tienda','Comercial','Tienda / minimercado',60,'empleados por día',3,312),
 ('papeleria','Comercial','Papelería / librería',40,'empleados por día',2,312),
 ('ferreteria','Comercial','Ferretería',45,'empleados por día',4,312),
 ('oficina','Comercial','Oficina / consultorio administrativo',50,'empleados por día',10,260),
 ('restaurante','Comercial','Restaurante',20,'comidas por día',60,312),
 ('cafeteria','Comercial','Cafetería / panadería de venta',8,'servicios por día',60,312),
 ('peluqueria','Comercial','Peluquería',25,'clientes por día',15,312),
 ('lavadero','Comercial','Lavadero automático sin recirculación',208,'vehículos por día',20,312),
 ('lavanderia','Comercial','Lavandería',15,'kg de ropa por día',80,312),
 ('hotel','Comercial','Hotel / alojamiento',150,'huéspedes por día',20,365),
 ('gimnasio','Comercial','Gimnasio con duchas',40,'usuarios por día',80,312),
 ('comercial_general','Comercial','Otro comercio / actividad sin precisar',50,'empleados por día',4,312),
 ('confeccion','Industrial','Confección sin proceso húmedo',60,'trabajadores por día',15,260),
 ('carpinteria','Industrial','Carpintería sin proceso húmedo',60,'trabajadores por día',8,260),
 ('metalmecanica','Industrial','Taller metalmecánico sin enfriamiento húmedo',70,'trabajadores por día',10,260),
 ('alimentos','Industrial','Procesamiento de alimentos',10,'kg procesados por día',200,260),
 ('bebidas','Industrial','Producción de bebidas',4,'litros de producto por día',500,260),
 ('textil','Industrial','Lavado / acabado textil',60,'kg procesados por día',100,260),
 ('industrial_general','Industrial','Otra industria / proceso sin precisar',100,'trabajadores por día',10,260),
 ('colegio','Oficial','Colegio / institución educativa sin internado',25,'estudiantes y personal por día',200,200),
 ('sede_publica','Oficial','Sede administrativa pública',50,'funcionarios por día',30,260),
 ('salud','Oficial','Centro de salud ambulatorio',30,'atenciones por día',80,312),
 ('hospital','Oficial','Hospital con internación',600,'camas ocupadas por día',30,365),
 ('biblioteca','Oficial','Biblioteca / centro cultural',10,'visitantes y personal por día',100,260),
 ('deportivo','Oficial','Centro deportivo con duchas',40,'usuarios por día',100,312),
 ('oficial_general','Oficial','Otra entidad oficial',50,'personas por día',30,260),
]
CATALOG = {x[0]:dict(zip(('id','categoria','nombre','litros_unidad','unidad','cantidad_defecto','dias_defecto'),x)) for x in DEFINITIONS}
for item in CATALOG.values():
    item['fuente'] = EPA if item['id']=='lavadero' else 'Supuesto provisional HIDRO; requiere calibración local'
    item['version'] = VERSION

def norm(value):
    return ''.join(c for c in unicodedata.normalize('NFKD',str(value or '').casefold()) if not unicodedata.combining(c)).strip()

def validate_components(raw, use):
    if raw is None or raw=='':return None
    if not isinstance(raw,list) or len(raw)>30:raise ValueError('Consumo: máximo 30 actividades.')
    out=[]
    for i,c in enumerate(raw,1):
        if not isinstance(c,dict) or c.get('actividad') not in CATALOG:raise ValueError(f'Actividad {i}: selecciona una opción del catálogo.')
        p=CATALOG[c['actividad']]
        if use not in ('Mixto','Multiusuario','Multiuso') and p['categoria']!=use:raise ValueError(f'Actividad {i}: no corresponde al uso {use}.')
        row={'actividad':p['id']}
        for key,default,limit in [('cantidad',p['cantidad_defecto'],1000000),('dias_ano',p['dias_defecto'],365),('litros_unidad',p['litros_unidad'],1000000)]:
            v=c.get(key,default)
            if isinstance(v,bool):raise ValueError(f'Actividad {i}: {key} no válido.')
            try:v=float(v)
            except (TypeError,ValueError):raise ValueError(f'Actividad {i}: {key} debe ser numérico.')
            if not math.isfinite(v) or not 0<=v<=limit:raise ValueError(f'Actividad {i}: {key} fuera de rango (0–{limit}).')
            row[key]=v
        if p['categoria']=='Residencial':row.update(dias_ano=365,litros_unidad=90)
        out.append(row)
    return out or None

def components_for(r):
    explicit=r.get('componentes_consumo')
    if explicit:return explicit,False
    use=r.get('clase_uso');activity=norm(r.get('tipo_actividad'))
    if use=='Residencial':
        if r.get('numero_habitantes') is None:return [],False
        return [dict(actividad='vivienda',cantidad=r['numero_habitantes'],dias_ano=365,litros_unidad=90)],False
    match=next((p for p in CATALOG.values() if p['categoria']==use and activity and (activity==norm(p['id']) or activity==norm(p['nombre']))),None)
    if use in ('Mixto','Multiusuario','Multiuso'):
        # Explicitly visible provisional mix. Replace by real component inventory in editor.
        return [dict(actividad='vivienda',cantidad=r.get('numero_habitantes') if r.get('numero_habitantes') is not None else 4,dias_ano=365,litros_unidad=90),dict(actividad='comercial_general',cantidad=4*max(1,r.get('unidades_no_habitacionales') or 1),dias_ano=312,litros_unidad=50)],True
    p=match or CATALOG.get({'Comercial':'comercial_general','Industrial':'industrial_general','Oficial':'oficial_general'}.get(use))
    if not p:return [],False
    return [dict(actividad=p['id'],cantidad=p['cantidad_defecto'],dias_ano=p['dias_defecto'],litros_unidad=p['litros_unidad'])],True

def estimate(r):
    components,assumed=components_for(r);d90=d100=0;details=[]
    for c in components:
        p=CATALOG[c['actividad']];liters=c['litros_unidad'];qty=c['cantidad'];days=c['dias_ano']
        low=qty*liters*days/365/1000
        high=qty*(100 if p['categoria']=='Residencial' else liters)*days/365/1000
        d90+=low;d100+=high
        details.append({**c,'nombre':p['nombre'],'unidad':p['unidad'],'fuente':p['fuente'],'personalizado':liters!=p['litros_unidad'],'m3_dia_operacion':qty*liters/1000,'m3_ano':low*365})
    return dict(demanda_diaria_90_m3=d90 if components else None,demanda_diaria_100_m3=d100 if components else None,
        coeficiente_demanda=None,motivo_sin_demanda='' if components else 'Sin dato de habitantes o actividad',
        componentes_calculo=details,consumo_con_supuestos=assumed,metodo_consumo=VERSION,
        nota_consumo='Promedio diario anual: suma de cantidad × L/unidad × días/año ÷ 365 ÷ 1000. Solo la parte residencial cambia entre escenarios. '+('Cantidades y mezcla provisionales; revisar en Editar.' if assumed else 'Cantidades informadas; factores de referencia editables.'))
