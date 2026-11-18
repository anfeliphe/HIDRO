import { useState, useCallback, useRef, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import { Plus, Send, Sparkles } from 'lucide-react';
import * as api from '../api/client';
import { ChatMarkdown } from '../components/ChatMarkdown';

const CHAT_STORAGE_VERSION = 'v3-activities';
const CHAT_MAX_STORED = 100;

function chatStorageKey() {
  try {
    const id = localStorage.getItem('userId');
    return `webgis_chat_messages_${CHAT_STORAGE_VERSION}:${id || 'anon'}`;
  } catch {
    return `webgis_chat_messages_${CHAT_STORAGE_VERSION}:anon`;
  }
}

function loadPersistedMessages() {
  try {
    const raw = localStorage.getItem(chatStorageKey());
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .filter(
        (m) =>
          m &&
          (m.type === 'user' || m.type === 'ai') &&
          typeof m.text === 'string',
      )
      .slice(-CHAT_MAX_STORED);
  } catch {
    return [];
  }
}

function persistMessages(messages) {
  try {
    localStorage.setItem(
      chatStorageKey(),
      JSON.stringify(messages.slice(-CHAT_MAX_STORED)),
    );
  } catch {
    // Quota or private mode — ignore
  }
}

const suggestedQuestions = [
  "¿Cuál es la demanda total estimada del territorio?",
  "Demanda por uso del predio: residencial, comercial y mixto",
  "¿Cuál será la demanda en 5 años con un crecimiento del 3 %?",
  "Compara los escenarios de 90 y 100 litros por persona al día.",
];

async function getAnswerForQuestion(question, growthRate = 2, years = 5) {
 const q=question.toLowerCase();
 const n=v=>Number(v).toLocaleString('es-CO',{maximumFractionDigits:2});
 try{
  const rows=await api.apiFetch('/census/unified');
  const eligible=rows.filter(r=>r.demanda_diaria_90_m3!=null);
  const sum=(rs,key)=>rs.reduce((t,r)=>t+(r[key]??0),0);
  const daily=sum(eligible,'demanda_diaria_90_m3'),high=sum(eligible,'demanda_diaria_100_m3');
  const scope=`Cálculo sobre ${eligible.length} de ${rows.length} predios. Son estimaciones de demanda, no lecturas de medidores.`;
  if(/crecimiento|proyec|futur|años|forecast|growth/.test(q)){
   const rateMatch=q.match(/(\d+(?:[.,]\d+)?)\s*%/),yearMatch=q.match(/(\d+)\s*(?:años|years)/);
   const rate=rateMatch?Number(rateMatch[1].replace(',','.')):Number(growthRate);
   const horizon=yearMatch?Number(yearMatch[1]):Number(years);
   if(rate<0||rate>20||horizon<1||horizon>20)return 'Usa un crecimiento entre 0 y 20 % y un horizonte entre 1 y 20 años.';
   const factor=(1+rate/100)**horizon;
   return `**Proyección a ${horizon} años con ${n(rate)} % de crecimiento anual:**\n\n- 90 L/persona/día: **${n(daily*365*factor)} m³/año**.\n- 100 L/persona/día: **${n(high*365*factor)} m³/año**.\n\n${scope}`;
  }
  const threshold=q.match(/(?:más de|mas de|mayor que)\s+(\d+)\s*(?:personas|habitantes)/);
  if(threshold){const group=eligible.filter(r=>r.numero_habitantes>Number(threshold[1]));const amount=sum(group,'demanda_diaria_90_m3');return `**${group.length} predios con más de ${threshold[1]} habitantes:** ${n(amount*365)} m³/año en el escenario de 90 L/persona/día (${daily?n(amount/daily*100):'0'} % de la demanda).\n\n${scope}`;}
  if(/habitantes|población|personas|population/.test(q))return `**Habitantes informados:** ${n(sum(rows,'numero_habitantes'))}.\n\n${rows.filter(r=>r.numero_habitantes==null).length} predios sin dato de habitantes.`;
  if(/uso|residencial|comercial|mixto|tipo/.test(q))return '**Demanda diaria por uso (90 L/persona/día):**\n\n'+[...new Set(eligible.map(r=>r.clase_uso))].map(u=>`- ${u}: ${n(sum(eligible.filter(r=>r.clase_uso===u),'demanda_diaria_90_m3'))} m³/día.`).join('\n')+`\n\n${scope}`;
  if(/escenario|compara|diferencia/.test(q))return `**Comparación anual:**\n\n- 90 L/persona/día: ${n(daily*365)} m³/año.\n- 100 L/persona/día: ${n(high*365)} m³/año.\n- Diferencia: ${n((high-daily)*365)} m³/año.\n\n${scope}`;
  if(/total|demanda|consumo/.test(q))return `**Demanda estimada a 90 L/persona/día:**\n\n- Diaria: ${n(daily)} m³.\n- Mensual (30 días): ${n(daily*30)} m³.\n- Anual (365 días): ${n(daily*365)} m³.\n\n${scope}`;
  return 'Puedo consultar la demanda total, los habitantes, los usos del predio, las proyecciones y los escenarios. Selecciona una pregunta sugerida o indica qué dato deseas consultar.';
 }catch(e){return `No se pudieron cargar los datos: ${e.message}`;}
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 px-1 py-2" aria-hidden>
      <span className="chat-dot h-2 w-2 rounded-full bg-gray-400" />
      <span className="chat-dot h-2 w-2 rounded-full bg-gray-400" />
      <span className="chat-dot h-2 w-2 rounded-full bg-gray-400" />
    </div>
  );
}

const Chat = () => {
  const outletContext = useOutletContext() || {};
  const growthRate = outletContext.growthRate ?? 2;
  const projectionYears = outletContext.projectionYears ?? 5;
  const [messages, setMessages] = useState(loadPersistedMessages);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [images,setImages]=useState([]),[imageLoading,setImageLoading]=useState(false),[attachError,setAttachError]=useState('');
  const [useWeb,setUseWeb]=useState(true),[caps,setCaps]=useState(null);
  useEffect(()=>{api.apiFetch('/chat/capabilities').then(c=>{setCaps(c);if(!c.web)setUseWeb(false);}).catch(()=>{setCaps({configured:false,images:false,web:false});setUseWeb(false);});},[]);
  async function attach(e){
    const files=Array.from(e.target.files||[]);e.target.value='';setAttachError('');
    if(images.length+files.length>2){setAttachError('Puedes adjuntar hasta 2 imágenes por mensaje.');return;}
    if(files.some(f=>!['image/png','image/jpeg','image/webp'].includes(f.type)||f.size>4*1024*1024)){setAttachError('Utiliza PNG, JPEG o WEBP de hasta 4 MB por imagen.');return;}
    setImageLoading(true);
    try{const loaded=await Promise.all(files.map(f=>new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve({name:f.name,data:r.result});r.onerror=reject;r.readAsDataURL(f);})));setImages(v=>[...v,...loaded]);}catch{setAttachError('No se pudo leer la imagen.');}finally{setImageLoading(false);}
  }
  const scrollRef = useRef(null);

  const startNewChat = useCallback(() => {
    if (loading||imageLoading) return;
    setMessages([]);
    setInput('');setImages([]);setAttachError('');
  }, [loading,imageLoading]);

  useEffect(() => {
    persistMessages(messages);
  }, [messages]);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) {
      el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
    }
  }, [messages, loading]);

  const sendMessage = useCallback(
    async (textOverride) => {
      if (loading || imageLoading) return;
      const raw = textOverride !== undefined ? textOverride : input;
      const text = String(raw).trim() || (images.length?'Analiza estas imágenes con la información disponible en HIDRO.':'');
      if (!text) return;

      const userMessage = { type: 'user', text: text+(images.length?'\n\nImágenes adjuntas: '+images.map(i=>i.name).join(', '):'') };
      setMessages((prev) => [...prev, userMessage]);
      setInput('');
      setLoading(true);

      let answer;let sources=[];
      let usedFallback = false;
      try {
        // Pass short conversation history so follow-up questions can be interpreted consistently.
        const history = messages.slice(-8).map((m) => ({
          role: m.type === 'user' ? 'user' : 'assistant',
          content: m.text,
        }));
        const res = await api.chat(text, {
          growth_rate: growthRate,
          projection_years: projectionYears,
          history, images:images.map(i=>i.data), use_web:useWeb,
        });
        sources=res.sources||[];setImages([]);
        answer = res.reply || "El asistente no devolvió una respuesta.";
      } catch (err) {
        if(images.length||useWeb){answer=err.message+' Puedes volver a enviar el mensaje. Para consultar solo los indicadores sin IA, desactiva internet y retira las imágenes.';}else{usedFallback = true;answer = await getAnswerForQuestion(text, growthRate, projectionYears);}
      }
      const fallbackNotice = usedFallback
        ? '*Asistente no disponible. Respuesta calculada con los datos de HIDRO.*\n\n'
        : '';
      setMessages((prev) => [...prev, { type: 'ai', text: fallbackNotice + answer, sources }]);
      setLoading(false);
    },
    [input, growthRate, projectionYears, loading, messages, images, imageLoading, useWeb],
  );

  const handleSuggestedClick = (question) => {
    sendMessage(question);
  };

  const hasMessages = messages.length > 0;

  return (
    <div className="pro-chat flex h-full min-h-0 flex-col bg-gradient-to-b from-gray-50/80 to-white">
      <div className="shrink-0 border-b border-gray-200/70 bg-white/90 px-4 py-4 backdrop-blur-md sm:px-6 lg:pl-6 pl-4">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 shadow-md shadow-blue-500/20">
              <Sparkles className="h-4 w-4 text-white" strokeWidth={2} />
            </div>
            <div>
              <h2 className="text-lg font-semibold tracking-tight text-gray-900">Asistente HIDRO</h2>
              <p className="text-xs text-gray-500">Consulta predios, interpreta estimaciones y revisa información. El chat usa todos tus registros accesibles.</p>
            </div>
          </div>
          <button
            type="button"
            onClick={startNewChat}
            disabled={loading}
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 shadow-sm transition hover:border-blue-300 hover:text-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Plus size={14} />
            Nueva conversación
          </button>
        </div>
      </div>

      <div
        ref={scrollRef}
        className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden px-4 py-6 sm:px-6"
      >
        <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
          {!hasMessages && (
            <div className="animate-fade-in-up space-y-8">
              <div className="rounded-2xl border border-gray-200/80 bg-white p-8 text-center shadow-sm">
                <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/25">
                  <Sparkles className="h-7 w-7 text-white" />
                </div>
                <h3 className="mb-2 text-xl font-semibold text-gray-900">Conversa con tu territorio</h3>
                <p className="mx-auto max-w-md text-sm leading-relaxed text-gray-600">
                  Consulta totales, usos del predio, proyecciones y comparaciones en una conversación.
                </p>
              </div>
              <div>
                <p className="mb-3 text-center text-xs font-medium uppercase tracking-wide text-gray-500">
                  Preguntas sugeridas
                </p>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {suggestedQuestions.map((question, index) => (
                    <button
                      key={index}
                      type="button"
                      onClick={() => handleSuggestedClick(question)}
                      className="rounded-xl border border-gray-200 bg-white px-4 py-3 text-left text-sm text-gray-700 shadow-sm transition-all hover:border-blue-300 hover:bg-blue-50/50 hover:shadow-md"
                    >
                      {question}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {hasMessages && (
            <div className="flex flex-col gap-5 pb-4">
              {messages.map((msg, index) => (
                <div
                  key={index}
                  className={`flex w-full ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {msg.type === 'user' ? (
                    <div className="max-w-[min(100%,28rem)] whitespace-pre-wrap rounded-2xl rounded-br-md bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-2.5 text-[13px] leading-relaxed text-white shadow-md shadow-blue-600/20 sm:text-sm">
                      {msg.text}
                    </div>
                  ) : (
                    <div className="w-full max-w-[min(100%,40rem)]">
                      <p className="mb-1.5 text-xs font-medium text-gray-500">Asistente</p>
                      <div className="rounded-2xl rounded-bl-md border border-gray-100 bg-gray-50/90 px-4 py-3 shadow-sm ring-1 ring-gray-100/80">
                        <ChatMarkdown>{msg.text}</ChatMarkdown>
                        {msg.sources?.length>0&&<div className="mt-3 border-t pt-2 text-xs"><strong>Fuentes consultadas</strong>{msg.sources.filter(s=>/^https?:\/\//.test(s.url)).map(s=><a className="block text-blue-700 underline" href={s.url} target="_blank" rel="noreferrer" key={s.url}>{s.title||s.url}</a>)}</div>}
                      </div>
                    </div>
                  )}
                </div>
              ))}
              {loading && (
                <div className="flex w-full max-w-[min(100%,40rem)] flex-col">
                  <p className="mb-1.5 text-xs font-medium text-gray-500">Asistente</p>
                  <div className="rounded-2xl rounded-bl-md border border-gray-100 bg-gray-50/90 px-5 py-3 shadow-sm ring-1 ring-gray-100/80">
                    <TypingIndicator />
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="shrink-0 border-t border-gray-200/80 bg-white/95 px-4 py-4 backdrop-blur-md sm:px-6">
        <div className="mx-auto mb-3 max-w-3xl text-xs text-gray-600">
          <div className="flex flex-wrap items-center gap-4"><label className="cursor-pointer rounded-lg border px-3 py-2">Adjuntar imágenes<input className="sr-only" type="file" accept="image/png,image/jpeg,image/webp" multiple disabled={loading||imageLoading||caps?.images===false} onChange={attach}/></label>
          <label><input type="checkbox" checked={useWeb} disabled={loading||caps?.web===false} onChange={e=>setUseWeb(e.target.checked)}/> Consultar internet si es necesario</label><span>Prioridad: datos de HIDRO</span></div>
          {caps?.configured===false&&<p role="status" className="mt-2 text-amber-800">Imágenes e internet requieren configurar el servicio de IA en el servidor.</p>}
          <p className="mt-2">Al enviar, las imágenes y los datos consultados se procesan con el servicio de IA. Las imágenes no se guardan en el censo ni en el historial; adjúntalas otra vez para revisarlas en otro mensaje.</p>
          {images.length>0&&<div className="flex gap-3 py-2">{images.map((img,i)=><div key={i}><img src={img.data} alt={img.name} className="h-20 w-24 rounded-lg object-cover"/><button disabled={loading} type="button" onClick={()=>setImages(v=>v.filter((_,j)=>j!==i))}>Quitar {img.name}</button></div>)}</div>}
          {(attachError||imageLoading)&&<p role="alert">{attachError||'Leyendo imágenes…'}</p>}
        </div>
        <div className="mx-auto flex max-w-3xl items-end gap-2 rounded-2xl border border-gray-200 bg-gray-50/80 p-1.5 pl-3 shadow-inner ring-1 ring-gray-100 focus-within:border-blue-300 focus-within:ring-blue-100">
          <textarea
            rows={1}
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              e.target.style.height = 'auto';
              e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
            }}
            onKeyDown={(e) => {
              if (e.key !== 'Enter' || e.shiftKey || loading) return;
              e.preventDefault();
              sendMessage();
            }}
            placeholder="Escribe tu pregunta…"
            className="max-h-40 min-h-[44px] flex-1 resize-none bg-transparent py-2.5 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none"
          />
          <button
            type="button"
            onClick={() => sendMessage()}
            disabled={loading || imageLoading || (!input.trim()&&!images.length)}
            className="mb-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-md transition hover:from-blue-700 hover:to-indigo-700 disabled:cursor-not-allowed disabled:opacity-40"
            aria-label="Enviar"
          >
            <Send size={18} />
          </button>
        </div>
        <p className="mx-auto mt-2 max-w-3xl text-center text-[11px] text-gray-400">
          Estimaciones basadas en los predios; no corresponden a lecturas de medidores en tiempo real.
        </p>
      </div>
    </div>
  );
};

export default Chat;
