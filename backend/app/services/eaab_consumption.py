"""Transcripción del anexo EAAB. Referencias de recuperación, no aforos ni tarifas."""
import math
from datetime import date
DIAMETERS=['1/2','3/4','1','1 1/2','2','3','4','6']
ROWS=[
('alimentos','Alimentos',[72,273,646,1659,3394,8144,20564,48732]),
('alojamiento','Alojamiento, hotel, motel',[78,294,694,1784,3650,8759,22116,52410]),
('educativo','Centro Educativo',[80,303,717,1842,3767,9041,22827,54095]),
('hospital','Clínica Hospital',[52,198,467,1201,2456,5894,14881,35264]),
('construccion','Construcción',[87,329,779,2001,4093,9822,24800,58771]),
('curtiembres','Curtiembres',[71,269,636,1635,3344,8026,20265,48024]),
('gasolina','Estación de gasolina',[127,480,1134,2915,5963,14310,36132,85626]),
('imprenta','Imprenta y afines',[25,94,222,570,1166,2799,7068,16750]),
('lavadero','Lavadero de vehículos o motos',[99,373,882,2267,4637,11128,28098,66586]),
('lavanderia','Lavandería',[57,217,514,1320,2700,6481,16363,38777]),
('maderas','Maderas',[33,126,298,767,1568,3763,9502,22518]),
('metalmecanica','Metalmecánica y minería',[30,114,270,693,1418,3403,8593,20364]),
('quimica','Química',[103,390,921,2367,4842,11621,29341,69533]),
('restaurante','Restaurante',[62,235,555,1426,2916,6997,17667,41868]),
('funerarios','Servicios funerarios',[101,381,901,2315,4735,11363,28691,67991]),
('supermercado','Supermercado',[38,142,336,864,1768,4243,10713,25387]),
('textiles','Textiles, hilanderías, tintorería',[34,129,306,785,1606,3855,9734,23068]),
('otras','Otras Actividades',[43,163,384,988,2021,4850,12245,29018])]
TABLE={key:dict(id=key,nombre=name,valores=dict(zip(DIAMETERS,values))) for key,name,values in ROWS}
WORK_2026=[(200,90),(500,180),(1000,320),(2000,530),(5000,1010),(10000,1650),(20000,2710),(30000,3610),(50000,5200)]
WORK_2024=WORK_2026[2:]
SUI='http://reportes.sui.gov.co/fabricaReportes/frameSet.jsp?idreporte=acu_com_096'
SCOPE='Referencia para recuperación de consumos no facturados. No es consumo medido ni liquidación económica. El equivalente anual supone 12 meses; el diario es anual / 365.'

def catalog():
    return dict(diametros=DIAMETERS,sectores=list(TABLE.values()),obra_2026=WORK_2026,obra_2024=WORK_2024,sui_url=SUI,alcance=SCOPE)

def number(raw,key,maximum,minimum=0):
    value=raw.get(key)
    if isinstance(value,bool):raise ValueError(f'EAAB: {key} no válido.')
    try:value=float(value)
    except (TypeError,ValueError):raise ValueError(f'EAAB: informa {key}.')
    if not math.isfinite(value) or not minimum<=value<=maximum:raise ValueError(f'EAAB: {key} fuera de rango.')
    return value

def validate(raw,use):
    if raw is None:return None
    if not isinstance(raw,dict):raise ValueError('EAAB: configuración no válida.')
    if use=='Residencial':raise ValueError('Residencial: requiere NS-031; estas tablas son no residenciales.')
    version=raw.get('version')
    if version not in ('2024','2026'):raise ValueError('EAAB: selecciona versión 2024 o 2026.')
    out=dict(version=version,metodo=raw.get('metodo'))
    found=raw.get('fecha_hallazgo')
    if found:
        try:d=date.fromisoformat(found)
        except (TypeError,ValueError):raise ValueError('EAAB: fecha del hallazgo no válida.')
        if d<date(2024,6,21):raise ValueError('EAAB: hallazgo anterior a las versiones disponibles.')
        out['fecha_hallazgo']=found
    method=out['metodo']
    if method in ('tabla1','sui'):
        if raw.get('diametro') not in DIAMETERS:raise ValueError('EAAB: informa el diámetro; no se interpola entre columnas.')
        out['diametro']=raw['diametro']
        if use in ('Mixto','Multiuso','Multiusuario'):
            if raw.get('alcance_confirmado') is not True:raise ValueError('EAAB: confirma que corresponde a un suscriptor no residencial independiente; no sumes actividades de una acometida compartida.')
            out['alcance_confirmado']=True
        if method=='tabla1':
            if raw.get('sector') not in TABLE:raise ValueError('EAAB: selecciona un sector económico.')
            out['sector']=raw['sector']
        else:
            if version!='2026' or use not in ('Comercial','Mixto','Multiuso','Multiusuario'):raise ValueError('SUI: aplica a comercio no intensivo según numeral 5.2.b de 2026.')
            points=number(raw,'puntos_hidraulicos',3,1)
            if not points.is_integer() or raw['diametro']!='1/2' or raw.get('no_intensivo') is not True or raw.get('fuera_anexo') is not True:raise ValueError('SUI: requiere ½ pulgada, hasta 3 puntos, actividad no intensiva y no incluida en anexo.')
            out.update(puntos_hidraulicos=points,no_intensivo=True,fuera_anexo=True,promedio_m3_mes=number(raw,'promedio_m3_mes',1000000))
            for key in ('fuente_sui','periodo_sui','fecha_consulta'):
                value=raw.get(key)
                if not isinstance(value,str) or not value.strip() or len(value)>500:raise ValueError(f'SUI: informa {key}.')
                out[key]=value.strip()
            try:date.fromisoformat(out['fecha_consulta'])
            except ValueError:raise ValueError('SUI: fecha de consulta no válida.')
    elif method=='tabla2':
        out['area_m2']=number(raw,'area_m2',50000,0.000001)
    else:raise ValueError('EAAB: método desconocido.')
    return out

def calculate(raw,use):
    c=validate(raw,use)
    if c is None:raise ValueError('EAAB: selecciona un método.')
    version=c['version'];method=c['metodo']
    source=f"EAAB · Resolución {'0267 de 2026' if version=='2026' else '0464 de 2024'} · Anexo"
    result=dict(demanda_diaria_90_m3=None,demanda_diaria_100_m3=None,coeficiente_demanda=None,componentes_calculo=[],consumo_con_supuestos=False,metodo_consumo='EAAB-'+version+'-'+method,nota_consumo=SCOPE,motivo_sin_demanda='',fuente_consumo=source)
    if method=='tabla2':
        total=next(v for limit,v in (WORK_2026 if version=='2026' else WORK_2024) if c['area_m2']<=limit)
        result.update(consumo_total_obra_m3=total,motivo_sin_demanda='Volumen total de obra: excluido de demanda diaria y anual.',nota_consumo='Tabla 2: referencia de volumen total de obra, no mensual. No incluye selección de anomalías ni comparación de tablas del numeral 5.3. Revisar licencia, TPO, fuentes adicionales y área real antes de una liquidación.')
    else:
        monthly=TABLE[c['sector']]['valores'][c['diametro']] if method=='tabla1' else c['promedio_m3_mes']
        daily=monthly*12/365
        result.update(consumo_mensual_referencia_m3=monthly,demanda_diaria_90_m3=daily,demanda_diaria_100_m3=daily)
        if method=='sui':result['fuente_consumo']+=f" · SUI {c['periodo_sui']} · consultado {c['fecha_consulta']} · {c['fuente_sui']}"
    return result
