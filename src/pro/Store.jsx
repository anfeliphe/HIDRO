import {createContext,useContext,useState,useCallback,useEffect,useRef} from 'react';
import {apiFetch} from '../api/client';
import {stored,persist} from './data';
const Context=createContext(null);
export const useHidro=()=>useContext(Context);
export function HidroProvider({children}){
 const [rows,setRows]=useState([]),[loading,setLoading]=useState(true),[error,setError]=useState(''),[lastSync,setLastSync]=useState(null),[notice,setNotice]=useState('');
 const [preferences,setPreferences]=useState(()=>stored('preferences',{scenario:90,growth:2,years:5,pageSize:20,project:'Gestión del territorio',reducedMotion:false}));
 const request=useRef(0);
 const refresh=useCallback(async()=>{const id=++request.current;setLoading(true);setError('');try{const data=await apiFetch('/census/unified');if(id===request.current){setRows(data);setLastSync(new Date());}}catch(e){if(id===request.current)setError(e.message);}finally{if(id===request.current)setLoading(false);}},[]);
 useEffect(()=>{refresh();return()=>{request.current++;};},[refresh]);
 useEffect(()=>{if(!notice)return;const t=setTimeout(()=>setNotice(''),6500);return()=>clearTimeout(t);},[notice]);
 function updatePreferences(next){const p={...preferences,...next};setPreferences(p);const saved=persist('preferences',p);setNotice(saved?'Preferencias guardadas en este navegador.':'No se pudo guardar la preferencia en este navegador.');}
 return <Context.Provider value={{rows,loading,error,lastSync,refresh,preferences,updatePreferences,notice,setNotice}}>{children}</Context.Provider>;
}
