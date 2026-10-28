"""Invented scoring examples only. No real instrument, normative or clinical claims."""
from pathlib import Path
import csv,json

ROOT=Path(__file__).parent

def bands(lo,mid,hi):
    return [dict(id='lower',label='Lower example band',lower=lo,upper=mid,upper_inclusive=False,
                 text='The configured example score is {{score}}. It falls in the {{band}}.'),
            dict(id='upper',label='Upper example band',lower=mid,upper=hi,upper_inclusive=True,
                 text='The configured example score is {{score}}. It falls in the {{band}}.')]

def base(name,title,n,lo,hi):
    return dict(schema_version='1.0',questionnaire_id=name,title=title,instrument_version='synthetic_v1',
                scoring_reference='Invented demonstration rules supplied in this package. Not a validated questionnaire.',
                id_column='participant_id',introduction='This report demonstrates the software using invented items and thresholds. The example bands have no clinical or normative meaning.',
                missing_codes=['',None,'NA',99],items=[dict(id=f'q{i}',column=f'q{i}',min=lo,max=hi) for i in range(1,n+1)],scales=[])

def configurations():
    a=base('likert_demo','Synthetic learning routine example',4,0,4)
    a['items'][1]['reverse']=True
    for sid,label,method,hi,mid in [('total','Example total','sum',16,8),('average','Example average','mean',4,2)]:
        a['scales'].append(dict(id=sid,label=label,items=['q1','q2','q3','q4'],method=method,bands=bands(0,mid,hi),interpretation_reference='Invented example bands; no population norms.'))
    a['sections']=[dict(id='context_message',title='Example conditional message',
        text='This paragraph appears only when the total is at least eight and the first item is at most one.',source='Invented cross-score demonstration rule.',
        when={'all':[{'scale':'total','op':'ge','value':8},{'item':'q1','op':'le','value':1}]})]
    b=base('weighted_mean_demo','Synthetic service experience example',4,0,3)
    for i in b['items']:i['recode']={'never':0,'sometimes':1,'often':2,'always':3}
    b['scales']=[dict(id='service',label='Example weighted average',items=['q1','q2','q3','q4'],method='weighted_mean',
        weights={'q1':1,'q2':2,'q3':1,'q4':2},bands=bands(0,1.5,3),interpretation_reference='Invented example bands; no population norms.')]
    c=base('knowledge_demo','Synthetic knowledge scoring example',5,0,1)
    for i in c['items']:i['recode']={'A':1,'B':0}
    c['scales']=[dict(id='percent',label='Example percentage',items=[f'q{i}' for i in range(1,6)],method='sum',multiplier=20,
        bands=bands(0,60,100),interpretation_reference='Invented example threshold; not a pass standard.')]
    d=base('prorated_demo','Synthetic routine checklist example',4,1,5)
    d['items'][1]['reverse']=True
    d['scales']=[dict(id='routine',label='Example weighted total',items=['q1','q2','q3','q4'],method='weighted_sum',weights={'q1':1,'q2':2,'q3':1,'q4':2},
        missing_policy={'method':'prorate','minimum_answered':3,'justification':'This invented demonstration explicitly permits weight-adjusted proration when at least three items are answered.'},
        bands=bands(6,18,30),interpretation_reference='Invented example bands; no population norms.')]
    out={'likert':a,'weighted_mean':b,'knowledge':c,'prorated':d}
    out.update(extended_configurations())
    return out

# ---------------------------------------------------------------------------------------------------------------
# Schema 1.1 examples: count rules, lookup (norm) tables, computed items and dynamic report text.
# Every item, threshold, table and sentence below is invented; none reproduces a real instrument.

NORM_GROUPS = {'adult_female': (11, 3.0), 'adult_male': (10, 3.2), 'youth': (12, 3.5)}   # invented mean and SD of raw sums

def invented_t(raw, mean, sd):
    """Invented T-score: 50 + 10 (raw - mean) / sd, rounded half up. Demonstration only."""
    from decimal import Decimal, ROUND_HALF_UP
    return int((Decimal(50) + Decimal(10) * (Decimal(raw) - Decimal(str(mean))) / Decimal(str(sd))).quantize(Decimal(1), rounding=ROUND_HALF_UP))

def two_bands(lo, mid, hi, ref='Invented example bands; no population norms.'):
    return bands(lo, mid, hi), ref

def extended_configurations():
    out = {}
    # Count rule: how many items meet a threshold, plus a rule that also requires item 1 or item 2.
    e = base('count_rule_demo', 'Synthetic symptom count example', 6, 0, 3)
    e['schema_version'] = '1.1'
    e['scales'] = [
        dict(id='count', label='Example count of items at threshold', items=[f'q{i}' for i in range(1, 7)], method='count',
             criterion=dict(op='ge', value=2), item_criteria={'q6': dict(op='ge', value=1)},
             bands=bands(0, 4, 6), interpretation_reference='Invented example threshold; not a diagnostic algorithm.'),
        dict(id='total', label='Example total', items=[f'q{i}' for i in range(1, 7)], method='sum',
             bands=bands(0, 9, 18), interpretation_reference='Invented example bands; no population norms.')]
    e['sections'] = [dict(id='pattern', title='Example combined rule',
        text='This paragraph appears when at least four items meet their threshold and item 1 or item 2 is one of them.',
        source='Invented rule with the structure of a count-based screening algorithm.',
        when={'all': [{'scale': 'count', 'op': 'ge', 'value': 4},
                      {'any': [{'item': 'q1', 'op': 'ge', 'value': 2}, {'item': 'q2', 'op': 'ge', 'value': 2}]}]})]
    out['count_rule'] = e
    # Lookup table: raw sum converted to an invented T-score, with a different table for each norm group.
    f = base('norm_table_demo', 'Synthetic norm-referenced example', 4, 1, 5)
    f['schema_version'] = '1.1'
    f['variables'] = [dict(id='age', column='age', type='numeric', min=12, max=90),
                      dict(id='sex', column='sex', type='categorical', codes=['F', 'M'])]
    tables = []
    for gid, (mean, sd) in NORM_GROUPS.items():
        group = {'variable': 'age', 'op': 'lt', 'value': 18} if gid == 'youth' else \
            {'all': [{'variable': 'age', 'op': 'ge', 'value': 18}, {'variable': 'sex', 'op': 'eq', 'value': 'F' if gid == 'adult_female' else 'M'}]}
        tables.append(dict(id=gid, group=group, type='exact', rows=[dict(raw=r, score=invented_t(r, mean, sd)) for r in range(4, 21)]))
    scores = [row['score'] for t in tables for row in t['rows']]
    f['scales'] = [dict(id='t_score', label='Example converted score', items=['q1', 'q2', 'q3', 'q4'], method='sum',
        missing_policy=dict(method='prorate', minimum_answered=3,
                            justification='This invented demonstration prorates when at least three items are answered and rounds the raw score up before conversion.'),
        lookup=dict(reference='Invented conversion tables; not a published norm.', round_raw='up', tables=tables),
        display_decimals=0, bands=bands(min(scores), 60, max(scores)), interpretation_reference='Invented example cut-off on the converted score.')]
    out['norm_table'] = f
    # Computed items: clock times and durations turned into component scores, then summed.
    g = base('sleep_diary_demo', 'Synthetic sleep diary example', 2, 0, 3)
    g['schema_version'] = '1.1'
    g['missing_codes'] = ['', None, 'NA']   # 99 is a valid latency in minutes, so it cannot also mean missing
    g['variables'] = [dict(id='bedtime', column='bedtime', type='time'), dict(id='waketime', column='waketime', type='time'),
                      dict(id='latency', column='latency_min', type='numeric', min=0, max=240),
                      dict(id='sleep_hours', column='sleep_hours', type='numeric', min=0, max=16, allow_decimal=True)]
    g['derived_items'] = [
        dict(id='c_duration', label='Sleep duration component', compute={'variable': 'sleep_hours'}, min=0, max=3,
             bins=[dict(lower=None, upper=5, value=3), dict(lower=5, upper=6, value=2),
                   dict(lower=6, upper=7, upper_inclusive=True, value=1), dict(lower=7, upper=None, value=0)]),
        dict(id='c_latency', label='Sleep latency component', compute={'variable': 'latency'}, min=0, max=3,
             bins=[dict(lower=None, upper=16, value=0), dict(lower=16, upper=31, value=1),
                   dict(lower=31, upper=61, value=2), dict(lower=61, upper=None, value=3)]),
        dict(id='in_bed', label='Minutes in bed', compute={'op': 'minutes_between', 'args': [{'variable': 'bedtime'}, {'variable': 'waketime'}]},
             min=0, max=1439),
        dict(id='c_efficiency', label='Sleep efficiency component',
             compute={'op': 'mul', 'args': [{'op': 'div', 'args': [{'op': 'mul', 'args': [{'variable': 'sleep_hours'}, {'const': 60}]},
                                                                    {'item': 'in_bed'}]}, {'const': 100}]},
             min=0, max=3, bins=[dict(lower=None, upper=65, value=3), dict(lower=65, upper=75, value=2),
                                 dict(lower=75, upper=85, value=1), dict(lower=85, upper=None, value=0)])]
    g['scales'] = [dict(id='global', label='Example global score', items=['c_duration', 'c_latency', 'c_efficiency', 'q1', 'q2'],
        method='sum', bands=bands(0, 6, 15), interpretation_reference='Invented example bands; no population norms.')]
    out['sleep_diary'] = g
    # Dynamic report text: response wording, the highest-rated item in a domain, and scores inside sentences.
    h = base('dynamic_text_demo', 'Synthetic dynamic feedback example', 0, 1, 5)
    h['schema_version'] = '1.1'
    h['items'] = [dict(id='duration', column='duration', min=1, max=4,
                       response_labels={'1': 'less than a month', '2': 'one to six months', '3': 'six to twelve months', '4': 'more than a year'})]
    reasons = ['Example reason A1', 'Example reason A2', 'Example reason A3', 'Example reason B1', 'Example reason B2', 'Example reason B3']
    for i, label in enumerate(reasons, 1):
        h['items'].append(dict(id=f'r{i}', column=f'r{i}', min=1, max=5, label=label))
    h['scales'] = [dict(id='area_a', label='Example area A', items=['r1', 'r2', 'r3'], method='mean',
                        bands=bands(1, 3, 5), interpretation_reference='Invented example threshold.'),
                   dict(id='area_b', label='Example area B', items=['r4', 'r5', 'r6'], method='mean',
                        bands=bands(1, 3, 5), interpretation_reference='Invented example threshold.')]
    h['sections'] = [
        dict(id='duration_text', title='Example duration sentence', text='You told us this has lasted {{length}}.',
             source='Invented wording for each response option.', fill={'length': {'response_label': 'duration'}}),
        dict(id='top_a', title='Example area A', text='In area A, the reason you rated highest was {{top}}.',
             source='Invented rule: name the highest-rated item; name all tied items.', when={'scale': 'area_a', 'op': 'ge', 'value': 3},
             fill={'top': {'top_items': 'area_a', 'ties': 'all'}}),
        dict(id='top_b', title='Example area B', text='In area B, the reason you rated highest was {{top}}.',
             source='Invented rule: name the highest-rated item; withhold the sentence when items tie.', when={'scale': 'area_b', 'op': 'ge', 'value': 3},
             fill={'top': {'top_items': 'area_b', 'ties': 'withhold'}}),
        dict(id='summary', title='Example summary', text='Your area A score was {{score}} ({{band}}).',
             source='Invented summary sentence.', fill={'score': {'score': 'area_a'}, 'band': {'band': 'area_a'}})]
    out['dynamic_text'] = h
    return out

HEADERS = {'norm_table': ['participant_id', 'age', 'sex', 'q1', 'q2', 'q3', 'q4'],
           'sleep_diary': ['participant_id', 'bedtime', 'waketime', 'latency_min', 'sleep_hours', 'q1', 'q2'],
           'dynamic_text': ['participant_id', 'duration', 'r1', 'r2', 'r3', 'r4', 'r5', 'r6']}

def extended_rows():
    return {
        'count_rule': [['DEMO401', 3, 1, 2, 2, 0, 1], ['DEMO402', 1, 1, 2, 3, 3, 0], ['DEMO403', 2, 'NA', 2, 2, 2, 2]],
        'norm_table': [['DEMO501', 34, 'F', 3, 4, 2, 5], ['DEMO502', 16, 'M', 2, 'NA', 1, 2], ['DEMO503', 40, 'NA', 3, 3, 3, 3]],
        'sleep_diary': [['DEMO601', '23:30', '06:45', 20, 6.5, 1, 2], ['DEMO602', '01:15', '07:00', 45, 4.5, 2, 3],
                        ['DEMO603', '22:00', '22:00', 10, 7, 0, 0]],
        'dynamic_text': [['DEMO701', 3, 4, 2, 4, 3, 5, 2], ['DEMO702', 1, 2, 1, 1, 4, 4, 2]]}

def main():
    out=ROOT/'examples';out.mkdir(exist_ok=True)
    for name,c in configurations().items():
        (out/(name+'.json')).write_text(json.dumps(c,indent=2),encoding='utf-8')
    rows={
        'likert':[['DEMO001',1,2,3,4],['DEMO002',0,'NA',1,2],['DEMO003',0,1,999,1]],
        'weighted_mean':[['DEMO101','never','sometimes','often','always']],
        'knowledge':[['DEMO201','A','B','A','A','B']],
        'prorated':[['DEMO301',5,'NA',1,3],['DEMO302','NA','NA',1,3]]}
    rows.update(extended_rows())
    for name,r in rows.items():
        with (out/(name+'.csv')).open('w',newline='',encoding='utf-8') as f:
            header=HEADERS.get(name,['participant_id']+[f'q{i}' for i in range(1,len(r[0]))])
            w=csv.writer(f);w.writerow(header);w.writerows(r)

if __name__=='__main__':main()
