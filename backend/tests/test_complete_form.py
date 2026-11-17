import asyncio
import unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from app.database import Base,get_db
from app.api.census import router,CensusRecord,validate_manual_record
from app.api.deps import get_current_user_id
from app.models.parcel import Parcel

class CompleteFormTest(unittest.TestCase):
    def test_full_lifecycle_and_user_isolation(self):
        engine=create_async_engine('sqlite+aiosqlite:///:memory:')
        sessions=async_sessionmaker(engine,expire_on_commit=False)
        async def seed():
            async with engine.begin() as c:await c.run_sync(Base.metadata.create_all)
            async with sessions() as s:
                s.add(Parcel(parcel_id='OLD',land_use='Commercial',population=4,lat=4.5,lng=-74.2));await s.commit()
        asyncio.run(seed())
        async def db():
            async with sessions() as s:yield s
        app=FastAPI();app.include_router(router);app.dependency_overrides[get_db]=db;app.dependency_overrides[get_current_user_id]=lambda:1
        c=TestClient(app)
        record=dict(id_predio_demo='NEW',clase_uso='Residencial',lat=4.6,lng=-74.1,numero_habitantes=6,numero_familias=2,unidades_habitacionales=2,unidades_no_habitacionales=1,total_unidades=3,tiene_agua=True,horas_servicio=12.5,tiene_medidor=False,dato_simulado=True,direccion='Calle de prueba',municipio='Bogotá',barrio='Prueba',fecha_censo='2026-11-17',plano='A',zona='B',manzana='C',tipo_actividad='Vivienda',tipo_punto='Individual',clasificacion='Habitado',tanque_reserva=True,disponibilidad_cajilla=False,id_usuario='E-1')
        self.assertEqual(c.post('/census/records',json={'record':record}).status_code,201)
        self.assertEqual(c.post('/census/records',json={'record':record}).status_code,409)
        row=next(r for r in c.get('/census/unified').json() if r['id_predio_demo']=='NEW')
        for k,v in record.items():self.assertEqual(row[k],v)
        self.assertAlmostEqual(row['demanda_diaria_90_m3'],.54)
        record.update(numero_habitantes=10,horas_servicio=24)
        self.assertEqual(c.put('/census/records/NEW',json={'record':record}).status_code,200)
        row=next(r for r in c.get('/census/unified').json() if r['id_predio_demo']=='NEW')
        self.assertAlmostEqual(row['demanda_diaria_90_m3'],.9)
        self.assertEqual(c.put('/census/records/NEW',json={'record':{**record,'id_predio_demo':'OTHER'}}).status_code,400)
        app.dependency_overrides[get_current_user_id]=lambda:2
        self.assertEqual(c.put('/census/records/NEW',json={'record':record}).status_code,404)
        self.assertEqual(len(c.get('/census/unified').json()),1)
        app.dependency_overrides[get_current_user_id]=lambda:1
        old=c.get('/census/unified').json()[1]
        old=next(r for r in c.get('/census/unified').json() if r['id_predio_demo']=='OLD')
        old['direccion']='Dirección completada'
        self.assertEqual(c.put('/census/records/OLD',json={'record':old}).status_code,200)
        saved=next(r for r in c.get('/census/unified').json() if r['id_predio_demo']=='OLD')
        self.assertAlmostEqual(saved['demanda_diaria_90_m3'],.432)
        self.assertIsNone(saved['tiene_agua'])
        from pathlib import Path
        content=(Path(__file__).parents[2]/'public/HIDRO_modelo_propuesto_DEMO.csv').read_text()
        self.assertEqual(c.post('/census/import',json={'content':content,'preview':False}).status_code,200)
        imported=next(r for r in c.get('/census/unified').json() if r['id_predio_demo']=='DEMO-P-001')
        imported['direccion']='Dirección editada';imported['numero_habitantes']=12
        self.assertEqual(c.put('/census/records/DEMO-P-001',json={'record':imported}).status_code,200)
        edited=next(r for r in c.get('/census/unified').json() if r['id_predio_demo']=='DEMO-P-001')
        self.assertEqual(edited['direccion'],'Dirección editada');self.assertTrue(edited['dato_simulado'])
        self.assertEqual(edited['numero_habitantes'],12)
        self.assertEqual(c.delete('/census/records/NEW').status_code,200)
        asyncio.run(engine.dispose())

    def test_validation_and_unknown_values(self):
        base=dict(id_predio_demo='A',clase_uso='Residencial',lat=0,lng=0)
        valid=validate_manual_record(base)
        self.assertIsNone(valid['numero_habitantes']);self.assertIsNone(valid['tiene_medidor'])
        for extra in [dict(lat=91),dict(numero_habitantes=-1),dict(numero_habitantes=2.5),dict(horas_servicio=25,tiene_agua=True),dict(horas_servicio=2,tiene_agua=False),dict(total_unidades=4,unidades_habitacionales=1,unidades_no_habitacionales=1),dict(fecha_censo='2026-99-99'),dict(tiene_agua='No')]:
            with self.assertRaises(ValueError):validate_manual_record({**base,**extra})
