import React,{useState} from 'react';
import {it,expect,vi,afterEach} from 'vitest';
import {render,screen,fireEvent,cleanup} from '@testing-library/react';
import EaabEditor from '../src/components/EaabEditor';
import ParcelForm from '../src/components/ParcelForm';
import {apiFetch} from '../src/api/client';
vi.mock('../src/api/client',()=>({apiFetch:vi.fn()}));
afterEach(cleanup);
const catalog={diametros:['1/2','3/4'],sectores:[{id:'lavadero',nombre:'Lavadero de vehículos o motos',valores:{'1/2':99,'3/4':373}}]};
it('previews monthly consumption with the exact selected diameter',async()=>{
 apiFetch.mockImplementation(async(path,options)=>path==='/census/eaab-catalog'?catalog:{consumo_mensual_referencia_m3:99,fuente_consumo:'EAAB · 2026'});
 function Wrapper(){const [value,setValue]=useState(null);return <EaabEditor use="Comercial" value={value} onChange={setValue}/>}
 render(<Wrapper/>);
 fireEvent.change(screen.getByLabelText('Método del predio'),{target:{value:'tabla1'}});
 await screen.findByText('Lavadero de vehículos o motos');
 fireEvent.change(screen.getByLabelText('Diámetro de acometida · pulgadas *'),{target:{value:'1/2'}});
 fireEvent.change(screen.getByLabelText('Sector económico *'),{target:{value:'lavadero'}});
 fireEvent.click(screen.getByText('Comprobar cálculo EAAB'));
 expect(await screen.findByRole('status')).toBeTruthy();
 expect(screen.getByRole('status').textContent).toContain('99 m³/suscriptor/mes');
 const [,options]=apiFetch.mock.calls.find(([p])=>p==='/census/eaab-preview');expect(JSON.parse(options.body).calculo_eaab.diametro).toBe('1/2');
 fireEvent.change(screen.getByLabelText('Diámetro de acometida · pulgadas *'),{target:{value:'3/4'}});
 expect(screen.queryByRole('status')).toBeNull();
});
it('preserves EAAB metadata when editing the record',async()=>{
 apiFetch.mockImplementation(async()=>catalog);
 const onSave=vi.fn().mockResolvedValue({});
 const c={version:'2026',metodo:'tabla1',sector:'lavadero',diametro:'3/4'};
 render(<ParcelForm record={{id_predio_demo:'P1',clase_uso:'Comercial',lat:4.6,lng:-74,calculo_eaab:c}} onSave={onSave} onClose={()=>{}}/>);
 await screen.findByText('Lavadero de vehículos o motos');
 fireEvent.click(screen.getByText('Guardar cambios'));
 expect(onSave).toHaveBeenCalledOnce();expect(onSave.mock.calls[0][0].calculo_eaab).toEqual(c);
});
