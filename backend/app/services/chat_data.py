"""Read-only query engine. Receives only rows already authorized for this user."""
import math
from app.services.activity_demand import norm
NUMERIC={'numero_habitantes','numero_familias','horas_servicio','unidades_habitacionales','unidades_no_habitacionales','total_unidades','demanda_diaria_90_m3','demanda_diaria_100_m3'}
FIELDS=NUMERIC|{'id_predio_demo','id_usuario','fecha_censo','plano','zona','barrio','manzana','municipio','direccion','clase_uso','tipo_actividad','tipo_punto','tiene_agua','tanque_reserva','disponibilidad_cajilla','clasificacion','tiene_medidor','dato_simulado','origen','lat','lng','consumo_con_supuestos'}

def query_records(rows, args):
    filters=args.get('filters') or []
    if not isinstance(filters,list) or len(filters)>10:return {'error':'Máximo 10 filtros.'}
    selected=rows
    for f in filters:
        field=f.get('field');op=f.get('op');value=f.get('value')
        if field not in FIELDS or op not in ['eq','contains','gt','lt','missing']:return {'error':'Campo u operador inválido.'}
        def match(r):
            v=r.get(field)
            if op=='missing':return v is None or v==''
            if op=='eq':return norm(v)==norm(value)
            if op=='contains':return norm(value) in norm(v)
            try:return v is not None and (float(v)>float(value) if op=='gt' else float(v)<float(value))
            except (ValueError,TypeError):return False
        selected=[r for r in selected if match(r)]
    group=args.get('group_by') or ''
    if group and group not in FIELDS:return {'error':'Agrupación inválida.'}
    def summary(rs):
        return {'predios':len(rs),'simulados':sum(r.get('dato_simulado') is True for r in rs),'con_supuestos':sum(bool(r.get('consumo_con_supuestos')) for r in rs),
            'sumas':{k:sum(r[k] for r in rs if r.get(k) is not None) for k in NUMERIC},
            'sin_dato':{k:sum(r.get(k) is None for r in rs) for k in NUMERIC}}
    output={'fuente':'HIDRO · datos autorizados del usuario','total_coincidencias':len(selected),'resumen':summary(selected),'alcance':'Los agregados usan TODAS las coincidencias; solo las fichas se paginan. Sumas de demanda: m³/día promedio anual. No sumar horas como indicador de servicio.'}
    if group:
        groups={}
        for r in selected:groups.setdefault(str(r.get(group)),[]).append(r)
        output['grupos']={k:summary(rs) for k,rs in groups.items()}
    try:offset=max(0,int(args.get('offset',0)))
    except (TypeError,ValueError):return {'error':'Página inválida.'}
    output['fichas']=selected[offset:offset+40]
    output['siguiente_offset']=offset+40 if offset+40<len(selected) else None
    return output

QUERY_TOOL={'type':'function','name':'consultar_hidro','description':'Consulta TODOS los predios accesibles. Filtra cualquier campo, devuelve agregados exactos y fichas paginadas. Usa identificador exacto para un predio. No extrapoles desde una página. Vacío devuelve resumen global.','parameters':{'type':'object','properties':{
 'filters':{'type':'array','items':{'type':'object','properties':{'field':{'type':'string','enum':sorted(FIELDS)},'op':{'type':'string','enum':['eq','contains','gt','lt','missing']},'value':{'type':'string'}},'required':['field','op','value'],'additionalProperties':False}},
 'group_by':{'type':'string','description':'Campo para agrupar; vacío para no agrupar.'},'offset':{'type':'integer','minimum':0}},'required':['filters','group_by','offset'],'additionalProperties':False},'strict':True}
