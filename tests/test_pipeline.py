import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('pipeline',ROOT/'src/pipeline.py')
p=importlib.util.module_from_spec(spec); spec.loader.exec_module(p)

class ReportingTests(unittest.TestCase):
    def test_seed_is_reproducible(self):
        self.assertEqual(p.generate(),p.generate())

    def test_quality_accounting_and_unique_grain(self):
        raw=p.generate(); clean,bad=p.clean(raw)
        self.assertEqual((len(raw),len(clean),len(bad)),(3249,3240,9))
        self.assertEqual(len(set(tuple(r[k] for k in p.FIELDS[:4]) for r in clean)),3240)
        self.assertEqual(sum(r['reason']=='duplicate grain' for r in bad),3)
        self.assertEqual(len(raw),len(clean)+len(bad))

    def test_sql_weighted_ratios_and_cents(self):
        rows=[dict(zip(p.FIELDS,['2026-09-01','A','Display','West',100,10,1,1000,3000])),dict(zip(p.FIELDS,['2026-09-02','A','Display','West',900,9,3,2000,6000]))]
        with tempfile.TemporaryDirectory() as tmp:
            con=p.database(rows,Path(tmp)/'test.sqlite')
            r=con.execute('SELECT * FROM campaign_kpis').fetchone()
            self.assertAlmostEqual(r['ctr'],.019)
            self.assertAlmostEqual(r['cvr'],4/19)
            self.assertAlmostEqual(r['cpa'],7.5)
            self.assertAlmostEqual(r['roas'],3)
            self.assertEqual(r['spend'],30)
            con.close()

    def test_zero_denominators_are_null(self):
        row=dict(zip(p.FIELDS,['2026-09-01','A','Display','West',0,0,0,0,0]))
        with tempfile.TemporaryDirectory() as tmp:
            con=p.database([row],Path(tmp)/'test.sqlite')
            r=con.execute('SELECT * FROM campaign_kpis').fetchone()
            for key in ['ctr','cvr','cpa','roas']: self.assertIsNone(r[key])
            con.close()

    def test_exports_reconcile_to_sql_and_periods(self):
        rows,_=p.clean(p.generate())
        with tempfile.TemporaryDirectory() as tmp:
            con=p.database(rows,Path(tmp)/'test.sqlite')
            self.assertEqual(con.execute('SELECT SUM(spend_cents) FROM campaign_daily').fetchone()[0],sum(r['spend_cents'] for r in rows))
            self.assertAlmostEqual(con.execute('SELECT SUM(spend) FROM channel_kpis').fetchone()[0],sum(r['spend_cents'] for r in rows)/100)
            self.assertEqual(con.execute('SELECT SUM(conversions) FROM period_kpis').fetchone()[0],sum(r['conversions'] for r in rows))
            video=list(con.execute("SELECT period,cvr FROM period_kpis WHERE channel='Online Video' ORDER BY period"))
            self.assertLess(video[1]['cvr'],video[0]['cvr'])
            con.close()

if __name__=='__main__': unittest.main()
