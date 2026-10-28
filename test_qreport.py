"""Computational verification against independent formulas for invented instruments.

This is not human review, psychometric validation or a clinical effectiveness study.
"""
import csv,io,itertools,json,tempfile,unittest
from copy import deepcopy
from pathlib import Path
from qreport import ReportEngine,ConfigurationError,DataError,render_html,load_config,score_rows,main
from make_examples import configurations,bands

COUNTS={'exhaustive_response_profiles':0,'scored_scale_comparisons':0,'unscorable_profiles_checked':0}

def record(values):return dict(participant_id='TEST001',**{f'q{i+1}':v for i,v in enumerate(values)})

class ScoringChecks(unittest.TestCase):
    def test_exhaustive_sum_mean_and_reverse(self):
        e=ReportEngine(configurations()['likert'])
        for values in itertools.product(range(5),repeat=4):
            r=e.score(record(values));expected=values[0]+(4-values[1])+values[2]+values[3]
            self.assertEqual(r['scales'][0]['score'],expected)
            self.assertEqual(r['scales'][1]['score'],expected/4)
            self.assertEqual(r['scales'][0]['band']['id'],'lower' if expected<8 else 'upper')
            self.assertEqual(len(r['sections']),int(expected>=8 and values[0]<=1))
            COUNTS['exhaustive_response_profiles']+=1;COUNTS['scored_scale_comparisons']+=2

    def test_exhaustive_weighted_mean_and_recoding(self):
        e=ReportEngine(configurations()['weighted_mean']);labels=['never','sometimes','often','always']
        for v in itertools.product(range(4),repeat=4):
            r=e.score(record([labels[x] for x in v]));expected=(v[0]+2*v[1]+v[2]+2*v[3])/6
            self.assertAlmostEqual(r['scales'][0]['score'],expected,places=12)
            self.assertEqual(r['scales'][0]['band']['id'],'lower' if expected<1.5 else 'upper')
            COUNTS['exhaustive_response_profiles']+=1;COUNTS['scored_scale_comparisons']+=1

    def test_exhaustive_binary_conversion(self):
        e=ReportEngine(configurations()['knowledge'])
        for v in itertools.product(['A','B'],repeat=5):
            r=e.score(record(v));expected=20*v.count('A')
            self.assertEqual(r['scales'][0]['score'],expected)
            self.assertEqual(r['scales'][0]['band']['id'],'lower' if expected<60 else 'upper')
            COUNTS['exhaustive_response_profiles']+=1;COUNTS['scored_scale_comparisons']+=1

    def test_exhaustive_proration_and_missingness(self):
        e=ReportEngine(configurations()['prorated']);w=[1,2,1,2]
        for v in itertools.product([None,1,2,3,4,5],repeat=4):
            r=e.score(record(v));s=r['scales'][0];n=sum(x is not None for x in v)
            if n<3:
                self.assertEqual(r['status'],'unscored');self.assertIsNone(s['score']);COUNTS['unscorable_profiles_checked']+=1
            else:
                x=[(6-z if j==1 else z) if z is not None else None for j,z in enumerate(v)]
                expected=sum(wj*z for wj,z in zip(w,x) if z is not None)*6/sum(wj for wj,z in zip(w,x) if z is not None)
                self.assertAlmostEqual(s['score'],expected,places=12)
                self.assertEqual(s['prorated'],n<4)
                COUNTS['scored_scale_comparisons']+=1
            COUNTS['exhaustive_response_profiles']+=1

    def test_zero_is_a_valid_response(self):
        r=ReportEngine(configurations()['likert']).score(record([0,0,0,0]))
        self.assertEqual(r['scales'][0]['score'],4);self.assertEqual(r['scales'][0]['answered'],4)

    def test_continuous_response_and_affine_conversion(self):
        c=configurations()['likert'];c['items'][0]['allow_decimal']=True
        c['scales']=c['scales'][:1];c['scales'][0].update(multiplier=1.5,offset=2,bands=bands(2,14,26))
        c['sections']=[]
        r=ReportEngine(c).score(record([.5,2,3,4]))
        self.assertEqual(r['scales'][0]['score'],16.25)
        self.assertEqual(r['scales'][0]['band']['id'],'upper')

    def test_word_export_contains_the_scored_values(self):
        from qreport import render_docx
        from docx import Document
        r=ReportEngine(configurations()['likert']).score(record([1,2,3,4]))
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'report.docx';render_docx(r,path);d=Document(path)
            self.assertEqual(d.tables[0].cell(1,1).text,'10')
            self.assertEqual(d.tables[0].cell(2,1).text,'2.5')
            self.assertIn(r['config_sha256'],'\n'.join(p.text for p in d.paragraphs))

    def test_invalid_values_block_release(self):
        e=ReportEngine(configurations()['likert'])
        for bad in ['bogus','NaN','Infinity',999,-1,0.5]:
            r=e.score(record([bad,0,0,0]));self.assertEqual(r['status'],'blocked')
            with self.assertRaises(DataError):render_html(r)

    def test_all_declared_missing_codes(self):
        e=ReportEngine(configurations()['likert'])
        for missing in ['',None,'NA',99,'99.0']:
            self.assertEqual(e.score(record([missing,0,0,0]))['status'],'unscored')

    def test_column_order_and_extra_metadata(self):
        e=ReportEngine(configurations()['likert']);r=record([1,2,3,4])
        reordered=dict(reversed(list(r.items())));reordered['unused']='ignored'
        self.assertEqual(e.score(r),e.score(reordered))

    def test_absent_columns_are_not_missing_answers(self):
        e=ReportEngine(configurations()['likert']);r=record([1,2,3,4]);del r['q2']
        with self.assertRaises(DataError):e.score(r)

    def test_subscale_partial_report(self):
        c=configurations()['likert'];c['scales'][1]['items']=['q1','q3']
        r=ReportEngine(c).score(record([1,None,3,4]))
        self.assertEqual(r['status'],'partial');self.assertIn('Not scored',render_html(r))

    def test_unknown_condition_is_not_true_under_not(self):
        c=configurations()['likert'];c['sections'][0]['when']={'not':{'item':'q2','op':'gt','value':1}}
        r=ReportEngine(c).score(record([1,None,3,4]))
        self.assertEqual(r['section_trace'][0]['decision'],'withheld_unknown');self.assertEqual(r['sections'],[])

    def test_short_csv_row_stops_the_batch(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td);cf=td/'config.json';cf.write_text(json.dumps(configurations()['prorated']))
            df=td/'input.csv';df.write_text('participant_id,q1,q2,q3,q4\nP1,1,2,3,4\nP2,1,2,3\n')
            with self.assertRaises(DataError):main(['--config',str(cf),'--data',str(df),'--out',str(td/'reports')])
            self.assertFalse((td/'reports').exists())

    def test_displayed_scores_are_rounded_and_decisions_use_exact_scores(self):
        c=configurations()['weighted_mean'];e=ReportEngine(c)
        r=e.score(record(['sometimes','never','never','never']));s=r['scales'][0]
        self.assertEqual(s['score_exact'],'0.1666666666666666666666666667');self.assertEqual(s['score_display'],'0.17')
        self.assertIn('score is 0.17.',s['text']);self.assertNotIn('0.1666',render_html(r))
        c['scales'][0]['display_decimals']=0;s=ReportEngine(c).score(record(['always','always','always','often']))['scales'][0]
        self.assertEqual(s['score_display'],'3');self.assertEqual(s['band']['id'],'upper')
        self.assertEqual(ReportEngine(configurations()['likert']).score(record([1,2,3,4]))['scales'][0]['score_display'],'10')
        for bad in [True,-1,7,1.5]:
            c=configurations()['weighted_mean'];c['scales'][0]['display_decimals']=bad
            with self.assertRaises(ConfigurationError):ReportEngine(c)

    def test_condition_operators_and_three_valued_logic(self):
        c=configurations()['likert']
        ops={'eq':lambda a,b:a==b,'ne':lambda a,b:a!=b,'lt':lambda a,b:a<b,'le':lambda a,b:a<=b,'gt':lambda a,b:a>b,'ge':lambda a,b:a>=b}
        c['sections']=[dict(id=f'{op}_{v}',title='t',text='x',source='s',when={'item':'q1','op':op,'value':v}) for op in ops for v in range(5)]
        e=ReportEngine(c)
        for q1 in range(5):
            got={t['id']:t['decision'] for t in e.score(record([q1,0,0,0]))['section_trace']}
            for op,f in ops.items():
                for v in range(5):self.assertEqual(got[f'{op}_{v}'],'included' if f(q1,v) else 'excluded')
        # Kleene truth tables: leaves that are true, false or unknown (q2 missing), combined under all, any and not
        leaf={True:{'item':'q1','op':'ge','value':0},False:{'item':'q1','op':'lt','value':0},None:{'item':'q2','op':'ge','value':0}}
        k_and=lambda a,b:False if False in (a,b) else None if None in (a,b) else True
        k_or=lambda a,b:True if True in (a,b) else None if None in (a,b) else False
        k_not=lambda a:None if a is None else not a
        name={True:'T',False:'F',None:'U'};expected={};c['sections']=[]
        for a in (True,False,None):
            for b in (True,False,None):
                for kind,node,want in (('all',{'all':[leaf[a],leaf[b]]},k_and(a,b)),('any',{'any':[leaf[a],leaf[b]]},k_or(a,b)),
                                       ('notall',{'not':{'all':[leaf[a],leaf[b]]}},k_not(k_and(a,b)))):
                    sid=f'{kind}_{name[a]}{name[b]}';expected[sid]=want
                    c['sections'].append(dict(id=sid,title='t',text='x',source='s',when=node))
        got={t['id']:t['decision'] for t in ReportEngine(c).score(record([2,None,0,0]))['section_trace']}
        for sid,want in expected.items():
            self.assertEqual(got[sid],{True:'included',False:'excluded',None:'withheld_unknown'}[want],sid)

    def test_proration_of_a_weighted_mean(self):
        c=configurations()['prorated'];c['scales'][0].update(method='weighted_mean',bands=bands(1,3,5))
        s=ReportEngine(c).score(record([5,None,1,3]))['scales'][0]
        self.assertEqual(s['score_exact'],'3');self.assertTrue(s['prorated']);self.assertEqual(s['band']['id'],'upper')
        s=ReportEngine(c).score(record([5,4,1,3]))['scales'][0]   # q2 is reverse-scored: 6 - 4 = 2
        self.assertAlmostEqual(s['score'],(5+2*2+1+2*3)/6,places=12);self.assertFalse(s['prorated']);self.assertEqual(s['band']['id'],'lower')

    def test_eligibility_and_manual_review_hold(self):
        c=configurations()['likert'];c['eligibility']=[dict(column='complete',equals=2,reason='Incomplete form')]
        e=ReportEngine(c);r=record([1,2,3,4]);r['complete']=1
        self.assertEqual(e.score(r)['status'],'blocked')
        c['scales'][0]['bands'][1]['hold']=True;e=ReportEngine(c);r['complete']=2
        result=e.score(r);self.assertEqual(result['status'],'held_for_review')
        with self.assertRaises(DataError):render_html(result)

    def test_duplicate_missing_and_unsafe_ids(self):
        e=ReportEngine(configurations()['likert']);r=record([1,2,3,4])
        with self.assertRaises(DataError):score_rows(e,[r,r])
        for value in [None,'','a\nb']:
            with self.assertRaises(DataError):e.score(dict(r,participant_id=value))

    def test_config_errors(self):
        changes=[lambda c:c.update(unknown_field=True),
                 lambda c:c['items'][0].update(reverse='yes'),
                 lambda c:c['scales'][0]['bands'][1].update(lower=9),
                 lambda c:c['scales'][0]['bands'][1].update(lower=7),
                 lambda c:c['scales'][0].update(items=['unknown']),
                 lambda c:c['scales'][0].update(weights={'q1':2}),
                 lambda c:c.update(missing_codes=[0]),
                 lambda c:c['items'][0].update(column='q2'),
                 lambda c:c['scales'][0]['bands'][0].update(text='{{unknown}}'),
                 lambda c:c['sections'][0].update(when={'scale':'missing','op':'gt','value':1})]
        for change in changes:
            c=configurations()['likert'];change(c)
            with self.assertRaises(ConfigurationError):ReportEngine(c)

    def test_proration_requires_explicit_rules(self):
        c=configurations()['prorated'];del c['scales'][0]['missing_policy']['justification']
        with self.assertRaises(ConfigurationError):ReportEngine(c)
        c=configurations()['prorated'];c['items'][0]['max']=6
        with self.assertRaises(ConfigurationError):ReportEngine(c)

    def test_duplicate_json_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'bad.json';p.write_text('{"schema_version":"1.0","schema_version":"2.0"}')
            with self.assertRaises(ConfigurationError):load_config(p)

    def test_decisions_are_deterministic_and_hash_tracks_rules(self):
        c=configurations()['likert'];e=ReportEngine(c);r=record([1,2,3,4])
        self.assertEqual(e.score(r),e.score(r))
        self.assertEqual(e.config_sha256,ReportEngine(json.loads(json.dumps(c))).config_sha256)
        c['instrument_version']='changed';self.assertNotEqual(e.config_sha256,ReportEngine(c).config_sha256)

    def test_html_escapes_text_and_preserves_provenance(self):
        c=configurations()['likert'];c['title']='<script>bad</script>'
        r=ReportEngine(c).score(record([1,2,3,4]));h=render_html(r)
        self.assertNotIn('<script>',h);self.assertIn('&lt;script&gt;',h)
        self.assertIn(r['config_sha256'],h);self.assertIn('10',h);self.assertIn('Example conditional message',h)

    def test_csv_batch_outputs_and_overwrite_guard(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td);cf=td/'config.json';cf.write_text(json.dumps(configurations()['likert']))
            df=td/'input.csv';df.write_text('participant_id,q1,q2,q3,q4\n../TEST,1,2,3,4\nBLOCKED,1,2,999,4\n')
            out=td/'reports'
            import contextlib
            with contextlib.redirect_stdout(io.StringIO()):main(['--config',str(cf),'--data',str(df),'--out',str(out)])
            m=json.loads((out/'run_manifest.json').read_text())
            self.assertEqual(m['status_counts'],{'ready':1,'blocked':1})
            self.assertEqual(len(list(out.glob('*.html'))),1)
            self.assertTrue(all('/' not in p.stem for p in out.iterdir()))
            with self.assertRaises(DataError):main(['--config',str(cf),'--data',str(df),'--out',str(out)])


if __name__=='__main__':
    import platform,time
    start=time.perf_counter();suite=unittest.defaultTestLoader.loadTestsFromTestCase(ScoringChecks)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    from qreport import VERSION
    summary=dict(engine_version=VERSION,python=platform.python_version(),tests_run=result.testsRun,
                 failures=len(result.failures),errors=len(result.errors),elapsed_seconds=time.perf_counter()-start,
                 **COUNTS,scope='Invented fixed-form instruments; computational verification only; no human or clinical validation.')
    target=Path(__file__).parent/'validation_results.json';target.write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2));raise SystemExit(0 if result.wasSuccessful() else 1)
