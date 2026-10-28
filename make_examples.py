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
    return {'likert':a,'weighted_mean':b,'knowledge':c,'prorated':d}

def main():
    out=ROOT/'examples';out.mkdir(exist_ok=True)
    for name,c in configurations().items():
        (out/(name+'.json')).write_text(json.dumps(c,indent=2),encoding='utf-8')
    rows={
        'likert':[['DEMO001',1,2,3,4],['DEMO002',0,'NA',1,2],['DEMO003',0,1,999,1]],
        'weighted_mean':[['DEMO101','never','sometimes','often','always']],
        'knowledge':[['DEMO201','A','B','A','A','B']],
        'prorated':[['DEMO301',5,'NA',1,3],['DEMO302','NA','NA',1,3]]}
    for name,r in rows.items():
        with (out/(name+'.csv')).open('w',newline='',encoding='utf-8') as f:
            w=csv.writer(f);w.writerow(['participant_id']+[f'q{i}' for i in range(1,len(r[0]))]);w.writerows(r)

if __name__=='__main__':main()
