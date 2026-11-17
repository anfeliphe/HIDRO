import asyncio
import base64
import io
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from PIL import Image
from app.database import Base,get_db
from app.api.census import router,validate_manual_record
from app.api.chat import router as chat_router,ChatRequest
from app.api.analytics import router as analytics_router
from app.api.deps import get_current_user_id
from app.services.activity_demand import estimate,validate_components,CATALOG
from app.services.chat_data import query_records
from app.services.import_parcels import parse_csv

class ActivityTest(unittest.TestCase):
    def test_units_and_mixed_no_double_count(self):
        store=estimate({'clase_uso':'Comercial','componentes_consumo':[dict(actividad='tienda',cantidad=3,litros_unidad=60,dias_ano=312)]})
        wash=estimate({'clase_uso':'Comercial','componentes_consumo':[dict(actividad='lavadero',cantidad=20,litros_unidad=208,dias_ano=312)]})
        self.assertAlmostEqual(store['demanda_diaria_90_m3']*365,56.16)
        self.assertAlmostEqual(wash['demanda_diaria_90_m3']*365,1297.92)
        self.assertEqual(wash['demanda_diaria_90_m3'],wash['demanda_diaria_100_m3'])
        mixed=estimate({'clase_uso':'Multiusuario','numero_habitantes':999,'componentes_consumo':[dict(actividad='vivienda',cantidad=4,litros_unidad=90,dias_ano=365),dict(actividad='tienda',cantidad=3,litros_unidad=60,dias_ano=312)]})
        self.assertAlmostEqual(mixed['demanda_diaria_90_m3'],.36+56.16/365)
        self.assertAlmostEqual(mixed['demanda_diaria_100_m3']-mixed['demanda_diaria_90_m3'],.04)
    def test_every_use_defaults_are_visible_and_zero_preserved(self):
        for use in ['Comercial','Industrial','Oficial','Multiusuario','Mixto']:
            r=estimate({'clase_uso':use});self.assertGreater(r['demanda_diaria_90_m3'],0);self.assertTrue(r['consumo_con_supuestos'])
        self.assertEqual(estimate({'clase_uso':'Residencial','numero_habitantes':0})['demanda_diaria_90_m3'],0)
        self.assertIsNone(estimate({'clase_uso':'Residencial'})['demanda_diaria_90_m3'])
    def test_components_validation(self):
        for component in [dict(actividad='lavadero',cantidad=-1),dict(actividad='lavadero',dias_ano=366),dict(actividad='lavadero',cantidad=float('nan')),dict(actividad='inventado')]:
            with self.assertRaises(ValueError):validate_components([component],'Comercial')
        with self.assertRaises(ValueError):validate_components([dict(actividad='lavadero')],'Industrial')
    def test_query_beyond_first_fifty(self):
        rows=[dict(id_predio_demo=f'P-{i}',numero_habitantes=i,clase_uso='Comercial',demanda_diaria_90_m3=2,demanda_diaria_100_m3=2) for i in range(120)]
        result=query_records(rows,{'filters':[dict(field='id_predio_demo',op='eq',value='P-119')]})
        self.assertEqual(result['fichas'][0]['numero_habitantes'],119)
        result=query_records(rows,{})
        self.assertEqual(len(result['fichas']),40);self.assertEqual(result['resumen']['sumas']['demanda_diaria_90_m3'],240)
        self.assertEqual(result['siguiente_offset'],40)
    def test_images_and_history_validation(self):
        b=io.BytesIO();Image.new('RGB',(2,2)).save(b,format='PNG');image='data:image/png;base64,'+base64.b64encode(b.getvalue()).decode()
        self.assertEqual(len(ChatRequest(message='Lee',images=[image]).images),1)
        for bad in ['https://example.com/a.png','data:image/png;base64,SGVsbG8=']:
            with self.assertRaises(ValueError):ChatRequest(message='Lee',images=[bad])
        with self.assertRaises(ValueError):ChatRequest(message='Lee',history=[{'role':'system','content':'bad'}])
    def test_legacy_csv_errors(self):
        header='parcel_id,land_use,population,lat,lng\n'
        with self.assertRaisesRegex(ValueError,'Fila 3'):parse_csv(header+'P,Residential,4,4,-74\np,Residential,3,4,-74')
        with self.assertRaises(ValueError):parse_csv(header+'P,Residential,3.5,4,-74')

class UpgradeAPITest(unittest.TestCase):
    def setUp(self):
        self.engine=create_async_engine('sqlite+aiosqlite:///:memory:');self.sessions=async_sessionmaker(self.engine,expire_on_commit=False)
        async def init():
            async with self.engine.begin() as c:await c.run_sync(Base.metadata.create_all)
        asyncio.run(init())
        async def db():
            async with self.sessions() as s:yield s
        self.app=FastAPI()
        for r in [router,chat_router,analytics_router]:self.app.include_router(r)
        self.app.dependency_overrides[get_db]=db;self.app.dependency_overrides[get_current_user_id]=lambda:1
        self.c=TestClient(self.app)
        self.record=dict(id_predio_demo='A',clase_uso='Comercial',lat=4.6,lng=-74.1,direccion='Calle 1 # 2-3',municipio='Bogotá',componentes_consumo=[dict(actividad='lavadero',cantidad=20,dias_ano=312,litros_unidad=208)])
    def tearDown(self):asyncio.run(self.engine.dispose())
    def test_duplicates_review_stale_token_and_isolation(self):
        self.assertEqual(self.c.post('/census/records',json={'record':self.record}).status_code,201)
        second={**self.record,'id_predio_demo':'B','direccion':'CL 1 2 3'}
        self.assertEqual(self.c.post('/census/records',json={'record':second}).status_code,409)
        review=self.c.post('/census/records',json={'record':second,'preview':True}).json()
        self.assertTrue(review['warnings'])
        changed={**second,'lat':4.601}
        self.assertEqual(self.c.post('/census/records',json={'record':changed,'review_token':review['review_token']}).status_code,409)
        self.assertEqual(self.c.post('/census/records',json={'record':second,'review_token':review['review_token']}).status_code,201)
        self.assertEqual(self.c.post('/census/records',json={'record':{**second,'id_predio_demo':' a '}}).status_code,409)
        self.app.dependency_overrides[get_current_user_id]=lambda:2
        self.assertEqual(self.c.get('/census/unified').json(),[])
        self.assertEqual(self.c.post('/census/records',json={'record':self.record}).status_code,201)
    def test_aggregate_and_form_volumes_agree(self):
        self.c.post('/census/records',json={'record':self.record})
        for scenario in [90,100]:
            summary=self.c.get(f'/analytics/summary?scenario={scenario}').json()
            self.assertAlmostEqual(summary['yearly']/1000,1297.92)
        self.assertEqual(self.c.get('/analytics/land-use').status_code,200)
    def test_pdf_uses_activity_totals(self):
        from app.api.export_report import _gather_report_payload
        from app.services.report_pdf import build_water_demand_report_pdf
        self.c.post('/census/records',json={'record':self.record})
        async def gather():
            async with self.sessions() as session:return await _gather_report_payload(session,90,2,5,None,1)
        payload=asyncio.run(gather())
        self.assertAlmostEqual(payload['summary']['yearly']/1000,1297.92)
        pdf=build_water_demand_report_pdf(payload,{'executive':'Prueba de actividades.','findings':'','recommendations':'','limitations':'Supuestos provisionales.'})
        self.assertTrue(pdf.startswith(b'%PDF-'))

    def test_csv_preserves_activity_and_invalid_import_is_atomic(self):
        import csv,json
        from pathlib import Path
        source=(Path(__file__).parents[2]/'public/HIDRO_modelo_propuesto_DEMO.csv').read_text()
        source_rows=list(csv.DictReader(io.StringIO(source)))
        row=source_rows[12];row['componentes_consumo']=json.dumps([dict(actividad='lavadero',cantidad=2,dias_ano=300,litros_unidad=208)])
        row['clase_uso']='Comercial'
        def pack(data):
            stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=list(data));writer.writeheader();writer.writerow(data);return stream.getvalue()
        self.assertEqual(self.c.post('/census/import',json={'content':pack(row),'preview':False}).status_code,200)
        key=row['id_predio_demo'];row.pop('componentes_consumo');row['tipo_actividad']='Actualización sin cambiar cálculo'
        review=self.c.post('/census/import',json={'content':pack(row)}).json()
        self.assertEqual(self.c.post('/census/import',json={'content':pack(row),'preview':False}).status_code,409)
        self.assertEqual(self.c.post('/census/import',json={'content':pack(row),'preview':False,'review_token':review['review_token']}).status_code,200)
        saved=self.c.get('/census/unified').json()[0]
        self.assertEqual(saved['componentes_consumo'][0]['cantidad'],2)
        self.assertAlmostEqual(saved['demanda_diaria_90_m3']*365,124.8)
        row['lat']='INVALIDA'
        self.assertEqual(self.c.post('/census/import',json={'content':pack(row),'preview':False}).status_code,400)
        self.assertEqual(self.c.get('/census/unified').json()[0]['lat'],saved['lat'])

    def test_no_key_and_mocked_query_tool(self):
        self.c.post('/census/records',json={'record':self.record})
        settings=SimpleNamespace(OPENAI_API_KEY='',CHAT_WEB_ENABLED=True,OPENAI_CHAT_MODEL='gpt-4.1-mini')
        with patch('app.api.chat.get_settings',return_value=settings):
            self.assertFalse(self.c.get('/chat/capabilities').json()['configured'])
            self.assertEqual(self.c.post('/chat',json={'message':'Hola'}).status_code,503)
        settings.OPENAI_API_KEY='test-not-real';calls=[]
        class FakeClient:
            def __init__(self,**kwargs):self.responses=self
            async def __aenter__(self):return self
            async def __aexit__(self,*args):pass
            async def create(self,**kwargs):
                calls.append(kwargs)
                if len(calls)==1:return SimpleNamespace(output=[SimpleNamespace(type='function_call',name='consultar_hidro',call_id='c1',arguments='{"filters":[],"group_by":"clase_uso","offset":0}')])
                return SimpleNamespace(output=[],output_text='Fuente: HIDRO, un predio.')
        with patch('app.api.chat.get_settings',return_value=settings),patch('openai.AsyncOpenAI',FakeClient):
            response=self.c.post('/chat',json={'message':'Consumo total','use_web':False})
            self.assertEqual(response.status_code,200,response.text)
            self.assertFalse(response.json()['used_web'])
            self.assertIn('1297',calls[1]['input'][-1]['output'])
            self.assertEqual([t['type'] for t in calls[1]['tools']],['function'])
