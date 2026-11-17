"""La edición desde la lista comparte datos con el mapa y los análisis."""
import asyncio
import unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.database import Base, get_db
from app.api.deps import get_current_user_id
from app.api.parcels import router as parcels_router
from app.api.census import router as census_router
from app.api.chat import ChatRequest

class ManualPrediosTest(unittest.TestCase):
    def test_create_and_edit_updates_unified_list(self):
        engine=create_async_engine('sqlite+aiosqlite:///:memory:')
        sessions=async_sessionmaker(engine,expire_on_commit=False)
        async def setup():
            async with engine.begin() as conn:await conn.run_sync(Base.metadata.create_all)
        asyncio.run(setup())
        async def db():
            async with sessions() as session:yield session
        app=FastAPI();app.include_router(parcels_router);app.include_router(census_router)
        app.dependency_overrides[get_db]=db
        app.dependency_overrides[get_current_user_id]=lambda:1
        client=TestClient(app)
        body=dict(parcel_id='PRUEBA-1',land_use='Residential',population=4,lat=4.5,lng=-74.2)
        self.assertIn(client.post('/parcels',json=body).status_code,(200,201))
        row=client.get('/census/unified').json()[0]
        self.assertEqual(row['origen'],'HIDRO existente')
        self.assertEqual(row['clase_uso'],'Residencial')
        self.assertAlmostEqual(row['demanda_diaria_90_m3'],.36)
        self.assertEqual(client.patch('/parcels/PRUEBA-1',json={'population':8,'land_use':'Commercial'}).status_code,200)
        rows=client.get('/census/unified').json()
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['numero_habitantes'],8)
        self.assertEqual(rows[0]['clase_uso'],'Comercial')
        self.assertAlmostEqual(rows[0]['demanda_diaria_90_m3'],4*50*312/365/1000)
        duplicate=client.post('/parcels',json=body)
        self.assertEqual(duplicate.status_code,400)
        self.assertEqual(duplicate.json()['detail'],'Ya existe un predio con ese identificador')
        self.assertEqual(client.delete('/parcels/PRUEBA-1').status_code,200)
        self.assertEqual(client.get('/census/unified').json(),[])
        self.assertEqual(client.delete('/parcels/PRUEBA-1').status_code,404)
        from pathlib import Path
        csv=(Path(__file__).parents[2]/'public/HIDRO_modelo_propuesto_DEMO.csv').read_text()
        self.assertEqual(client.post('/census/import',json={'content':csv,'preview':False}).status_code,200)
        app.dependency_overrides[get_current_user_id]=lambda:2
        self.assertEqual(client.delete('/census/records/DEMO-P-001').status_code,404)
        app.dependency_overrides[get_current_user_id]=lambda:1
        self.assertEqual(len(client.get('/census/unified').json()),18)
        self.assertEqual(client.delete('/census/records/DEMO-P-001').status_code,200)
        self.assertEqual(len(client.get('/census/unified').json()),17)
        self.assertEqual(client.delete('/census/records/DEMO-P-001').status_code,404)
        asyncio.run(engine.dispose())

    def test_forecast_understands_spanish(self):
        body=ChatRequest(message='Proyecta la demanda',growth_rate=3,projection_years=5)
        self.assertEqual((body.growth_rate,body.projection_years),(3,5))
