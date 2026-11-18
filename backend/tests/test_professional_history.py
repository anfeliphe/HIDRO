import asyncio
import unittest
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.database import Base,get_db
from app.api.census import router as census
from app.api.activity import router as activity
from app.api.parcels import router as parcels
from app.api.deps import get_current_user_id

class HistoryTest(unittest.TestCase):
 def setUp(self):
  self.engine=create_async_engine('sqlite+aiosqlite:///:memory:');self.sessions=async_sessionmaker(self.engine,expire_on_commit=False)
  async def init():
   async with self.engine.begin() as c:await c.run_sync(Base.metadata.create_all)
  asyncio.run(init())
  async def db():
   async with self.sessions() as s:yield s
  self.app=FastAPI()
  for router in [census,activity,parcels]:self.app.include_router(router)
  self.app.dependency_overrides[get_db]=db;self.app.dependency_overrides[get_current_user_id]=lambda:1
  self.c=TestClient(self.app);self.record=dict(id_predio_demo='TEST',clase_uso='Residencial',lat=4.5,lng=-74,numero_habitantes=4)
 def tearDown(self):asyncio.run(self.engine.dispose())
 def test_success_only_and_user_isolation(self):
  self.c.post('/census/records',json={'record':self.record,'preview':True})
  self.assertEqual(self.c.get('/activity').json()['total'],0)
  self.c.post('/census/records',json={'record':{**self.record,'lat':200}})
  self.assertEqual(self.c.get('/activity').json()['total'],0)
  self.assertEqual(self.c.post('/census/records',json={'record':self.record}).status_code,201)
  self.c.put('/census/records/TEST',json={'record':{**self.record,'numero_habitantes':5}})
  self.c.delete('/census/records/TEST')
  result=self.c.get('/activity').json()
  self.assertEqual([r['action'] for r in result['items']],['eliminacion','edicion','creacion'])
  self.app.dependency_overrides[get_current_user_id]=lambda:2
  self.assertEqual(self.c.get('/activity').json()['items'],[])
  self.app.dependency_overrides.pop(get_current_user_id)
  self.assertEqual(self.c.get('/activity').status_code,401)
 def test_csv_summary_and_pagination(self):
  sample=(Path(__file__).parents[2]/'public/HIDRO_modelo_propuesto_DEMO.csv').read_text()
  response=self.c.post('/census/import',json={'content':sample,'preview':False})
  self.assertEqual(response.status_code,200)
  result=self.c.get('/activity?limit=1').json()
  self.assertEqual(result['items'][0]['detail']['registros'],18)
  self.assertEqual(result['items'][0]['detail']['creados'],18)
  self.assertEqual(self.c.get('/activity?offset=1').json()['items'],[])
  self.assertEqual(self.c.get('/activity?limit=1000').status_code,422)
 def test_historic_operations_also_traced(self):
  body=dict(parcel_id='OLD',land_use='Residential',population=4,lat=4.5,lng=-74)
  self.assertEqual(self.c.post('/parcels',json=body).status_code,201)
  self.c.patch('/parcels/OLD',json={'population':6})
  self.c.delete('/parcels/OLD')
  result=self.c.get('/activity').json()
  self.assertEqual([r['action'] for r in result['items']],['eliminacion','edicion','creacion'])
