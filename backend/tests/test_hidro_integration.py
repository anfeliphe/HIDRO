import asyncio
import unittest
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.database import Base,get_db
from app.models.parcel import Parcel
from app.api.census import router as census_router
from app.api.analytics import router as analytics_router
from app.api.deps import get_current_user_id

class IntegrationTest(unittest.TestCase):
    def test_existing_and_imported_data_share_analytics_without_duplicates(self):
        engine=create_async_engine('sqlite+aiosqlite:///:memory:')
        sessions=async_sessionmaker(engine,expire_on_commit=False)
        async def seed():
            async with engine.begin() as c:await c.run_sync(Base.metadata.create_all)
            async with sessions() as s:
                s.add_all([Parcel(parcel_id='OLD-1',land_use='Residential',population=4,lat=4.5,lng=-74.2),Parcel(parcel_id='DEMO-P-001',land_use='Residential',population=100,lat=4.5,lng=-74.2)])
                await s.commit()
        asyncio.run(seed())
        async def db():
            async with sessions() as s:yield s
        app=FastAPI();app.include_router(census_router);app.include_router(analytics_router)
        app.dependency_overrides[get_db]=db;app.dependency_overrides[get_current_user_id]=lambda:1
        c=TestClient(app)
        content=(Path(__file__).parents[2]/'public/HIDRO_modelo_propuesto_DEMO.csv').read_text()
        self.assertEqual(c.post('/census/import',json={'content':content,'preview':False}).status_code,200)
        rows=c.get('/census/unified').json();self.assertEqual(len(rows),19)
        old=next(r for r in rows if r['id_predio_demo']=='OLD-1')
        self.assertIsNone(old['tiene_agua']);self.assertIsNone(old['dato_simulado'])
        self.assertEqual(sum(r['dato_simulado'] is True for r in rows),18)
        eligible=[r for r in rows if r['demanda_diaria_90_m3'] is not None]
        self.assertEqual(len(eligible),13)
        self.assertAlmostEqual(sum(r['demanda_diaria_90_m3'] for r in eligible),5.67)
        self.assertTrue(all(r['demanda_diaria_90_m3'] is None for r in rows if r['clase_uso']!='Residencial'))
        summary=c.get('/analytics/summary').json()
        self.assertAlmostEqual(summary['daily'],5670);self.assertEqual(summary['population'],63)
        for endpoint in ['forecast','land-use','scenario-comparison']:self.assertEqual(c.get('/analytics/'+endpoint).status_code,200)
        c.post('/census/import',json={'content':content,'preview':False})
        self.assertEqual(len(c.get('/census/unified').json()),19)
        app.dependency_overrides[get_current_user_id]=lambda:2
        self.assertEqual(len(c.get('/census/unified').json()),2)
        self.assertEqual(c.get('/analytics/summary').json()['population'],104)
        async def unchanged():
            async with sessions() as s:self.assertEqual((await s.execute(select(func.count(Parcel.id)))).scalar(),2)
        asyncio.run(unchanged());asyncio.run(engine.dispose())

if __name__=='__main__':unittest.main()
