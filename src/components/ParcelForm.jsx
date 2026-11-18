import EaabEditor from './EaabEditor';
import ActivityEditor from './ActivityEditor';
import {useEffect,useRef,useState} from 'react';
import {createPortal} from 'react-dom';
import {X,Building2} from 'lucide-react';

const groups=[
 ['Identificación y ubicación',[
 ['id_predio_demo','Identificador del predio','text'],['id_usuario','Identificador de encuesta','text'],['fecha_censo','Fecha del censo','date'],['direccion','Dirección','text'],['municipio','Municipio','text'],['barrio','Barrio o sector','text'],['zona','Zona','text'],['manzana','Manzana','text'],['plano','Plano','text'],['lat','Latitud','number',-90,90],['lng','Longitud','number',-180,180]]],
 ['Uso y características',[
 ['clase_uso','Uso del predio','use'],['tipo_actividad','Actividad','text'],['tipo_punto','Tipo de punto','text'],['clasificacion','Estado del inmueble','text'],['unidades_habitacionales','Unidades de vivienda','number',0,500],['unidades_no_habitacionales','Unidades no residenciales','number',0,500],['total_unidades','Total de unidades','number',0,1000],['numero_familias','Número de familias','number',0,50],['numero_habitantes','Número de habitantes','number',0,10000]]],
 ['Servicio de agua',[
 ['tiene_agua','Recibe agua de red EAAB','boolean'],['horas_servicio','Horas de suministro al día','number',0,24],['tanque_reserva','Tiene tanque de reserva','boolean'],['disponibilidad_cajilla','Dispone de espacio para cajilla','boolean'],['tiene_medidor','Tiene medidor','boolean']]],
 ['Origen de la información', [['dato_simulado','¿Es un dato simulado?','boolean']]]
];
const fields=groups.flatMap(g=>g[1]);
const required=new Set(['id_predio_demo','clase_uso','lat','lng']);
export default function ParcelForm({record,onSave,onClose,loading}){
 const [values,setValues]=useState(()=>Object.fromEntries(fields.map(([key])=>[key,record?.[key]??''])));
 const [components,setComponents]=useState(()=>record?.componentes_consumo||record?.componentes_calculo?.map(({actividad,cantidad,dias_ano,litros_unidad})=>({actividad,cantidad,dias_ano,litros_unidad}))||[]);
 const [eaab,setEaab]=useState(record?.calculo_eaab||null);
 const [error,setError]=useState('');const dialog=useRef(null);const saving=useRef(loading);saving.current=loading;
 useEffect(()=>{const previous=document.activeElement;dialog.current?.focus();const old=document.body.style.overflow;document.body.style.overflow='hidden';return()=>{document.body.style.overflow=old;previous?.focus();};},[]);
 function keyboard(e){if(e.key==='Escape'){e.preventDefault();if(!saving.current)onClose();}if(e.key==='Tab'){const nodes=[...dialog.current.querySelectorAll('button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled)')];const first=nodes[0],last=nodes[nodes.length-1];if(e.shiftKey&&(document.activeElement===first||document.activeElement===dialog.current)){e.preventDefault();last?.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus();}}}
 function change(key,val){if(key==='clase_uso'){setComponents([]);setEaab(null);};setValues(v=>({...v,[key]:val,...(key==='tiene_agua'&&val!=='true'?{horas_servicio:''}:{})}));}
 async function submit(e){e.preventDefault();if(loading)return;setError('');const payload={};for(const [key,,type] of fields){const v=values[key];payload[key]=v===''||v==null?null:type==='boolean'?(v===true||v==='true'):type==='number'?Number(v):String(v).trim();}payload.calculo_eaab=eaab;payload.componentes_consumo=values.clase_uso==='Residencial'?null:components.map(c=>({...c,cantidad:Number(c.cantidad),litros_unidad:Number(c.litros_unidad),dias_ano:Number(c.dias_ano)}));try{await onSave(payload);}catch(e){setError(e.message);}}
 return createPortal(<div className="hidro-form-overlay"><section ref={dialog} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby="parcel-form-title" className="hidro-parcel-form" onKeyDown={keyboard}>
 <header><div className="hidro-heading-icon"><Building2 size={23}/></div><div><h2 id="parcel-form-title">{record?'Editar predio':'Añadir predio'}</h2><p>Completa la ficha del predio. Los campos con * son obligatorios.</p></div><button type="button" aria-label="Cerrar formulario" disabled={loading} onClick={onClose}><X size={20}/></button></header>
 <form onSubmit={submit}><div className="hidro-form-body">
 {record?.origen==='HIDRO existente'&&<p className="hidro-form-info">La ficha completa se guardará en tu cuenta. El registro compartido original se conserva.</p>}
 {groups.map(([title,items])=><fieldset key={title} disabled={loading}><legend>{title}</legend><div className="hidro-form-grid">{items.map(([key,label,type,min,max])=>{const disabled=key==='horas_servicio'&&values.tiene_agua!==true&&values.tiene_agua!=='true';return <label key={key} htmlFor={'predio-'+key}><span>{label}{required.has(key)?' *':''}</span>{type==='boolean'?<select id={'predio-'+key} value={String(values[key])} onChange={e=>change(key,e.target.value)}><option value="">Sin información</option><option value="true">Sí</option><option value="false">No</option></select>:type==='use'?<select id={'predio-'+key} required value={values[key]} onChange={e=>change(key,e.target.value)}><option value="">Selecciona un uso</option>{['Residencial','Comercial','Mixto','Industrial','Oficial','Multiusuario','Multiuso'].map(v=><option key={v}>{v}</option>)}</select>:<input id={'predio-'+key} type={type} required={required.has(key)} readOnly={key==='id_predio_demo'&&!!record} disabled={disabled} min={min} max={max} step={['lat','lng','horas_servicio'].includes(key)?'any':1} maxLength={key==='id_predio_demo'?100:500} value={values[key]} placeholder={disabled?'No aplica':type==='text'?'Sin información':undefined} onChange={e=>change(key,e.target.value)}/>}</label>;})}</div></fieldset>)}
 {values.clase_uso&&values.clase_uso!=='Residencial'&&<EaabEditor value={eaab} onChange={setEaab} use={values.clase_uso} disabled={loading}/>}
 {values.clase_uso&&values.clase_uso!=='Residencial'&&!eaab&&<ActivityEditor use={values.clase_uso} components={components} onChange={setComponents} disabled={loading}/>}
 <p className="hidro-form-info">La demanda se calcula automáticamente. Los campos vacíos se conservan como datos no informados.</p>
 {error&&<p role="alert" className="hidro-form-error">{error}</p>}</div>
 <footer><button type="button" disabled={loading} onClick={onClose}>Cancelar</button><button className="hidro-save" type="submit" disabled={loading}>{loading?'Guardando…':record?'Guardar cambios':'Crear predio'}</button></footer></form>
 </section></div>,document.body);
}
