import {useEffect,useState} from 'react';
import {apiFetch} from '../api/client';
export default function ActivityEditor({use,components,onChange,disabled}){
 const [catalog,setCatalog]=useState([]),[error,setError]=useState('');
 useEffect(()=>{apiFetch('/census/activity-catalog').then(setCatalog).catch(e=>setError(e.message));},[]);
 const available=catalog.filter(p=>['Mixto','Multiusuario','Multiuso'].includes(use)||p.categoria===use);
 function setRow(i,patch){onChange(components.map((c,j)=>j===i?{...c,...patch}:c));}
 function defaults(p){return {actividad:p.id,cantidad:p.cantidad_defecto,dias_ano:p.dias_defecto,litros_unidad:p.litros_unidad};}
 const daily=components.reduce((s,c)=>s+Number(c.cantidad)*Number(c.litros_unidad)*Number(c.dias_ano)/365/1000,0);
 return <fieldset disabled={disabled}><legend>Estimación por actividad</legend>
 <p className="hidro-form-info">Selecciona la actividad y ajusta su tamaño. Los factores son referencias provisionales editables; no son consumos medidos ni valores oficiales EAAB. En usos mixtos, añade cada actividad una sola vez. Los factores por actividad incluyen servicios auxiliares de una operación pequeña; evita sumar el mismo personal otra vez.</p>
 {error&&<p role="alert">No se pudo cargar el catálogo: {error}</p>}
 {components.map((c,i)=>{const p=catalog.find(p=>p.id===c.actividad);return <div className="hidro-activity" key={i}><div className="hidro-form-grid">
 <label><span>Actividad {i+1}</span><select aria-label={`Actividad ${i+1}`} value={c.actividad} onChange={e=>setRow(i,defaults(catalog.find(p=>p.id===e.target.value)))}>{['Residencial','Comercial','Industrial','Oficial'].map(group=><optgroup key={group} label={group}>{available.filter(p=>p.categoria===group).map(p=><option value={p.id} key={p.id}>{p.nombre}</option>)}</optgroup>)}</select></label>
 <label><span>Cantidad · {p?.unidad}</span><input aria-label={`Cantidad actividad ${i+1}`} type="number" required min="0" max="1000000" step="any" value={c.cantidad} onChange={e=>setRow(i,{cantidad:e.target.value})}/></label>
 <label><span>Litros por unidad</span><input aria-label={`Factor actividad ${i+1}`} type="number" required min="0" max="1000000" step="any" readOnly={p?.categoria==='Residencial'} value={c.litros_unidad} onChange={e=>setRow(i,{litros_unidad:e.target.value})}/></label>
 <label><span>Días de operación al año</span><input aria-label={`Días actividad ${i+1}`} type="number" required min="0" max="365" step="any" readOnly={p?.categoria==='Residencial'} value={c.dias_ano} onChange={e=>setRow(i,{dias_ano:e.target.value})}/></label></div>
 <small>Referencia: {p?.fuente?.startsWith('https:')?<a href={p.fuente} target="_blank" rel="noreferrer">EPA · lavadero automático</a>:p?.fuente}. {p&&Number(c.litros_unidad)!==p.litros_unidad?'Factor personalizado.':''}</small>
 <button type="button" onClick={()=>onChange(components.filter((_,j)=>j!==i))}>Quitar actividad</button></div>;})}
 <button type="button" disabled={!available.length||components.length>=30} onClick={()=>onChange([...components,defaults(available[0])])}>+ Añadir actividad</button>
 <p className="hidro-form-info">{components.length?`Promedio estimado: ${daily.toLocaleString('es-CO',{maximumFractionDigits:3})} m³/día · ${(daily*365).toLocaleString('es-CO',{maximumFractionDigits:2})} m³/año. Fórmula: cantidad × litros/unidad × días/año.`:'Sin actividades definidas: se aplicará un perfil provisional del uso y quedará señalado en la ficha.'}</p>
 <details><summary>Consultar catálogo de usos y valores de referencia</summary><div className="census-table-scroll"><table><thead><tr><th>Tipo</th><th>Actividad</th><th>L/unidad</th><th>Unidad</th><th>Cantidad inicial</th><th>Días/año</th></tr></thead><tbody>{available.map(p=><tr key={p.id}><td>{p.categoria}</td><td>{p.nombre}</td><td>{p.litros_unidad}</td><td>{p.unidad}</td><td>{p.cantidad_defecto}</td><td>{p.dias_defecto}</td></tr>)}</tbody></table></div></details>
 </fieldset>;
}
