import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import pipeline as p

# These tiny records are tests only. Production artifacts use real Criteo data.
def record(**updates):
    row={'timestamp':'0','campaign':'10','conversion':'0','conversion_timestamp':'-1','conversion_id':'-1','attribution':'0','click':'0','cost':'0.00001'}
    row.update({k:str(v) for k,v in updates.items()})
    return row

def aggregate(day, impressions, clicks, conversions, post_click, cost):
    return dict(zip(p.FIELDS,[day,'A',impressions,clicks,conversions,post_click,cost]))

class ReportingTests(unittest.TestCase):
    def test_one_sale_linked_to_multiple_impressions_counted_once(self):
        rows=[record(timestamp=10,conversion=1,conversion_timestamp=90000,conversion_id=7,attribution=1,click=1),record(timestamp=86400,conversion=1,conversion_timestamp=90000,conversion_id=7,attribution=1,click=1),record(timestamp=87000,conversion=1,conversion_timestamp=90000,conversion_id=7,attribution=1)]
        groups,q,bad=p.ingest(rows)
        self.assertEqual(bad,[])
        self.assertEqual(q['unique_credited_conversions'],1)
        self.assertEqual(q['repeated_credited_conversion_links_collapsed'],2)
        self.assertEqual(groups[0]['conversions'],0)
        self.assertEqual(groups[1]['conversions'],1)
        self.assertEqual(groups[1]['post_click_conversions'],1)

    def test_reused_id_at_different_timestamps_stays_two_events(self):
        groups,q,_=p.ingest([record(conversion=1,conversion_timestamp=2,conversion_id=9,attribution=1,click=1),record(timestamp=3,conversion=1,conversion_timestamp=5,conversion_id=9,attribution=1,click=1)])
        self.assertEqual(q['unique_credited_conversions'],2)
        self.assertEqual(q['conversion_ids_with_multiple_timestamps'],1)
        self.assertEqual(q['unique_credited_conversion_ids'],1)
        self.assertEqual(groups[0]['conversions'],2)

    def test_no_observed_click_counts_in_cpa_not_click_cvr(self):
        groups,q,_=p.ingest([record(conversion=1,conversion_timestamp=2,conversion_id=9,attribution=1)])
        self.assertEqual(groups[0]['conversions'],1)
        self.assertEqual(groups[0]['post_click_conversions'],0)
        self.assertEqual(q['post_click_conversions'],0)

    def test_conversion_not_credited_to_criteo_is_not_counted(self):
        groups,q,_=p.ingest([record(conversion=1,conversion_timestamp=2,conversion_id=9,attribution=0,click=1)])
        self.assertEqual(groups[0]['conversions'],0)
        self.assertEqual(q['unique_observed_conversion_ids'],1)

    def test_validation_quarantines_source_positions_without_ids(self):
        groups,q,bad=p.ingest([record(),record(cost='NaN'),record(click=2),record(attribution=1),record(cost=-1),record(timestamp=-1),record(conversion=1,conversion_timestamp=1,conversion_id=-1)])
        self.assertEqual(q['source_rows'],7)
        self.assertEqual((q['accepted_rows'],q['quarantined_rows']),(1,6))
        self.assertEqual(set(bad[0]),{'source_line','reason'})
        self.assertEqual(sum(r['impressions'] for r in groups),1)

    def test_identical_impressions_are_not_deleted_without_event_id(self):
        groups,q,_=p.ingest([record(),record()])
        self.assertEqual(groups[0]['impressions'],2)
        self.assertEqual(q['quarantined_rows'],0)

    def test_cost_precision_and_unit_conversion(self):
        groups,_,_=p.ingest([record(cost='0.0000101234567'),record(cost='1e-05')])
        self.assertEqual(groups[0]['cost_scaled'],20123457)

    def test_global_conversion_dedupe_and_campaign_conflict_audit(self):
        groups,q,_=p.ingest([record(campaign=10,conversion=1,conversion_timestamp=5,conversion_id=3,attribution=1),record(campaign=20,timestamp=1,conversion=1,conversion_timestamp=5,conversion_id=3,attribution=1,click=1)])
        self.assertEqual(q['credited_conversion_keys_linked_to_multiple_campaigns'],1)
        self.assertEqual(sum(r['conversions'] for r in groups),1)
        self.assertEqual(next(r for r in groups if r['campaign']=='20')['conversions'],1)

    def test_sql_weighted_rates_and_explicit_conversion_denominators(self):
        rows=[aggregate(0,100,10,2,1,10*p.SCALE),aggregate(1,900,9,3,3,20*p.SCALE)]
        with tempfile.TemporaryDirectory() as tmp:
            con=p.database(rows,Path(tmp)/'test.sqlite')
            r=con.execute('SELECT * FROM campaign_kpis').fetchone()
            self.assertAlmostEqual(r['ctr'],.019)
            self.assertAlmostEqual(r['post_click_cvr'],4/19)
            self.assertAlmostEqual(r['cpa_transformed'],6)
            self.assertEqual(r['transformed_cost'],30)
            self.assertNotIn('roas',r.keys())
            con.close()

    def test_zero_denominators_are_null(self):
        with tempfile.TemporaryDirectory() as tmp:
            con=p.database([aggregate(0,1,0,0,0,1)],Path(tmp)/'test.sqlite')
            r=con.execute('SELECT * FROM campaign_kpis').fetchone()
            self.assertEqual(r['ctr'],0)
            for key in ['post_click_cvr','cpa_transformed','cpc_transformed']:
                self.assertIsNone(r[key])
            con.close()

    def test_committed_real_aggregates_reconcile_with_import_audit(self):
        rows,q,provenance=p.load_derived()
        p.validate_derived(rows,q)
        self.assertEqual(provenance['source_sha256'],p.SHA256)
        self.assertGreater(q['source_rows'],16_000_000)
        self.assertGreater(q['campaigns'],500)
        self.assertEqual(len(rows),q['daily_campaign_rows'])
        with tempfile.TemporaryDirectory() as tmp:
            con=p.database(rows,Path(tmp)/'test.sqlite')
            total=dict(con.execute('SELECT * FROM overall_kpis').fetchone())
            self.assertEqual(total['impressions'],q['accepted_rows'])
            self.assertEqual(total['conversions'],q['unique_credited_conversions'])
            self.assertAlmostEqual(total['transformed_cost'],q['total_cost_scaled']/p.SCALE)
            self.assertEqual(con.execute('SELECT SUM(clicks) FROM daily_kpis').fetchone()[0],q['total_clicks'])
            con.close()

if __name__=='__main__': unittest.main()
