import asyncio
import csv
import io
import unittest
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.api.census import router, parse_census, CensusRecord
from app.database import get_db, Base
from app.api.deps import get_current_user_id

SAMPLE=(Path(__file__).parents[2]/'public/HIDRO_modelo_propuesto_DEMO.csv').read_text()
def altered(key,value):
    reader=csv.DictReader(io.StringIO(SAMPLE));rows=list(reader);rows[0][key]=value
    out=io.StringIO();w=csv.DictWriter(out,fieldnames=reader.fieldnames);w.writeheader();w.writerows(rows);return out.getvalue()

class CensusTests(unittest.TestCase):
    def test_sample(self):
        rows=parse_census(SAMPLE);self.assertEqual(len(rows),18)
        self.assertEqual(sum(r['numero_habitantes'] or 0 for r in rows),59)
        self.assertIsNone(rows[12]['numero_habitantes'])
        self.assertTrue(all(r['dato_simulado'] for r in rows))
    def test_bom_and_semicolon(self):
        self.assertEqual(len(parse_census('\ufeff'+SAMPLE.replace(',',';'))),18)
    def test_bad_rows(self):
        for key,value in [('lat',''),('lng','nan'),('numero_habitantes','-1'),('numero_familias','1.5'),('horas_servicio','25'),('dato_simulado','quizas'),('clase_uso','Mixed-use'),('total_unidades','50'),('fecha_censo','no-fecha')]:
            with self.subTest(key=key),self.assertRaises(ValueError):parse_census(altered(key,value))
    def test_duplicates(self):
        with self.assertRaises(ValueError):parse_census(SAMPLE+SAMPLE.splitlines()[1]+'\n')
    def test_empty(self):
        with self.assertRaises(ValueError):parse_census('')
    def test_api_atomicity_upsert_and_isolation(self):
        engine=create_async_engine('sqlite+aiosqlite:///:memory:')
        sessions=async_sessionmaker(engine,expire_on_commit=False)
        async def initialize():
            async with engine.begin() as c:await c.run_sync(Base.metadata.create_all)
        asyncio.run(initialize())
        async def session():
            async with sessions() as s:yield s
        app=FastAPI();app.include_router(router);app.dependency_overrides[get_db]=session
        client=TestClient(app)
        self.assertEqual(client.get('/census').status_code,401)
        app.dependency_overrides[get_current_user_id]=lambda:1
        self.assertEqual(client.post('/census/import',json={'content':SAMPLE}).json()['inserted'],18)
        self.assertEqual(client.get('/census').json(),[])
        self.assertEqual(client.post('/census/import',json={'content':SAMPLE,'preview':False}).json()['inserted'],18)
        review=client.post('/census/import',json={'content':altered('numero_habitantes','9')}).json()
        self.assertEqual(client.post('/census/import',json={'content':altered('numero_habitantes','9'),'preview':False,'review_token':review['review_token']}).json()['updated'],18)
        self.assertEqual(len(client.get('/census').json()),18)
        self.assertEqual(client.get('/census').json()[0]['numero_habitantes'],9)
        self.assertEqual(client.post('/census/import',json={'content':altered('lat','bad'),'preview':False}).status_code,400)
        self.assertEqual(len(client.get('/census').json()),18)
        app.dependency_overrides[get_current_user_id]=lambda:2
        self.assertEqual(client.get('/census').json(),[])
        asyncio.run(engine.dispose())

if __name__=='__main__':unittest.main()
