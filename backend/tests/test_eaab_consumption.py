import unittest
import csv
import io
import json
from app.services.eaab_consumption import calculate,validate,TABLE,DIAMETERS
from app.services.activity_demand import estimate
import test_activity_upgrade as fixtures

class EaabCalculationTest(unittest.TestCase):
    def config(self,**kw):return dict(version='2026',metodo='tabla1',sector='lavadero',diametro='1/2',**kw)
    def test_all_table_cells_and_units(self):
        self.assertEqual(len(TABLE),18)
        for sector in TABLE.values():
            for d in DIAMETERS:
                c=self.config();c.update(sector=sector['id'],diametro=d)
                r=calculate(c,'Comercial')
                self.assertEqual(r['consumo_mensual_referencia_m3'],sector['valores'][d])
                self.assertAlmostEqual(r['demanda_diaria_90_m3']*365,sector['valores'][d]*12)
                self.assertEqual(r['demanda_diaria_90_m3'],r['demanda_diaria_100_m3'])
        self.assertEqual(TABLE['lavadero']['valores']['1/2'],99)
        self.assertEqual(TABLE['restaurante']['valores']['1/2'],62)
        self.assertEqual(TABLE['supermercado']['valores']['6'],25387)
    def test_eaab_wins_without_double_count(self):
        r=estimate(dict(clase_uso='Comercial',calculo_eaab=self.config(),componentes_consumo=[dict(actividad='lavadero',cantidad=99,litros_unidad=208,dias_ano=365)]))
        self.assertAlmostEqual(r['demanda_diaria_90_m3']*365,1188)
    def test_boundaries_and_historical_version(self):
        for area,total in [(200,90),(200.01,180),(500,180),(500.01,320),(1000,320),(1000.01,530),(50000,5200)]:
            r=calculate(dict(version='2026',metodo='tabla2',area_m2=area),'Industrial')
            self.assertEqual(r['consumo_total_obra_m3'],total)
            self.assertIsNone(r['demanda_diaria_90_m3'])
        self.assertEqual(calculate(dict(version='2024',metodo='tabla2',area_m2=100),'Industrial')['consumo_total_obra_m3'],320)
        for area in (0,-1,50001,float('nan'),float('inf'),True):
            with self.assertRaises(ValueError):calculate(dict(version='2026',metodo='tabla2',area_m2=area),'Industrial')
    def test_validation_no_invented_diameter_or_residential_rate(self):
        for patch in [dict(diametro=''),dict(diametro='1.25'),dict(sector='tienda'),dict(version='2025')]:
            with self.assertRaises(ValueError):validate({**self.config(),**patch},'Comercial')
        with self.assertRaises(ValueError):validate(self.config(),'Residencial')
        with self.assertRaises(ValueError):validate(self.config(),'Mixto')
        self.assertTrue(validate(self.config(alcance_confirmado=True),'Mixto')['alcance_confirmado'])
    def test_sui_requires_evidence_and_eligibility(self):
        c=dict(version='2026',metodo='sui',diametro='1/2',puntos_hidraulicos=3,no_intensivo=True,fuera_anexo=True,promedio_m3_mes=12.5,fuente_sui='Reporte EAAB SUI',periodo_sui='2026-10',fecha_consulta='2026-11-18')
        self.assertEqual(calculate(c,'Comercial')['consumo_mensual_referencia_m3'],12.5)
        for patch in [dict(puntos_hidraulicos=4),dict(diametro='3/4'),dict(fuera_anexo=False),dict(no_intensivo=False),dict(fecha_consulta='bad'),dict(fuente_sui=''),dict(version='2024')]:
            with self.assertRaises(ValueError):calculate({**c,**patch},'Comercial')

class EaabApiTest(unittest.TestCase):
    setUp=fixtures.UpgradeAPITest.setUp
    tearDown=fixtures.UpgradeAPITest.tearDown
    def test_save_edit_summary_and_csv(self):
        c=dict(version='2026',metodo='tabla1',sector='lavadero',diametro='1/2')
        record={**self.record,'calculo_eaab':c}
        self.assertEqual(self.c.post('/census/records',json={'record':record}).status_code,201)
        r=self.c.get('/census/unified').json()[0]
        self.assertEqual(r['calculo_eaab'],c)
        self.assertEqual(r['consumo_mensual_referencia_m3'],99)
        self.assertAlmostEqual(self.c.get('/analytics/summary').json()['yearly']/1000,1188)
        self.assertAlmostEqual(self.c.get('/analytics/summary').json()['monthly']/1000,99)
        record['calculo_eaab']={**c,'diametro':'3/4'}
        self.assertEqual(self.c.put('/census/records/A',json={'record':record}).status_code,200)
        self.assertEqual(self.c.get('/census/unified').json()[0]['consumo_mensual_referencia_m3'],373)
    def test_preview_validation_and_catalog(self):
        self.assertEqual(len(self.c.get('/census/eaab-catalog').json()['sectores']),18)
        self.assertEqual(self.c.post('/census/eaab-preview',json={}).status_code,400)
        r=self.c.post('/census/eaab-preview',json=dict(clase_uso='Oficial',calculo_eaab=dict(version='2026',metodo='tabla1',sector='educativo',diametro='1')))
        self.assertEqual(r.json()['consumo_mensual_referencia_m3'],717)
    def test_csv_roundtrip_preservation_and_bad_import_atomicity(self):
        from test_census import SAMPLE
        row=list(csv.DictReader(io.StringIO(SAMPLE)))[12]
        row['clase_uso']='Comercial'
        c=dict(version='2026',metodo='tabla1',sector='lavadero',diametro='1/2')
        row['calculo_eaab']=json.dumps(c)
        def pack(row):
            s=io.StringIO();w=csv.DictWriter(s,fieldnames=list(row));w.writeheader();w.writerow(row);return s.getvalue()
        self.assertEqual(self.c.post('/census/import',json={'content':pack(row),'preview':False}).status_code,200)
        self.assertEqual(self.c.get('/census/unified').json()[0]['calculo_eaab'],c)
        row.pop('calculo_eaab')
        preview=self.c.post('/census/import',json={'content':pack(row)}).json()
        self.assertEqual(self.c.post('/census/import',json={'content':pack(row),'preview':False,'review_token':preview['review_token']}).status_code,200)
        self.assertEqual(self.c.get('/census/unified').json()[0]['calculo_eaab'],c)
        row['calculo_eaab']=json.dumps({**c,'diametro':'5'})
        self.assertEqual(self.c.post('/census/import',json={'content':pack(row),'preview':False}).status_code,400)
        self.assertEqual(self.c.get('/census/unified').json()[0]['consumo_mensual_referencia_m3'],99)
    def test_pdf_uses_exact_monthly_reference_and_excludes_work(self):
        import asyncio
        from app.api.export_report import _gather_report_payload
        from app.services.report_pdf import build_water_demand_report_pdf
        record={**self.record,'calculo_eaab':dict(version='2026',metodo='tabla1',sector='lavadero',diametro='1/2')}
        self.c.post('/census/records',json={'record':record})
        async def gather():
            async with self.sessions() as s:return await _gather_report_payload(s,90,2,5,None,1)
        payload=asyncio.run(gather())
        self.assertAlmostEqual(payload['summary']['monthly']/1000,99)
        self.assertTrue(build_water_demand_report_pdf(payload,{}).startswith(b'%PDF'))
        record['calculo_eaab']=dict(version='2026',metodo='tabla2',area_m2=200)
        self.c.put('/census/records/A',json={'record':record})
        self.assertEqual(self.c.get('/analytics/summary').json()['yearly'],0)
        self.assertEqual(self.c.get('/census/unified').json()[0]['consumo_total_obra_m3'],90)
