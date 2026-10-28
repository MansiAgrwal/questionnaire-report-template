"""Configurable fixed-form questionnaire scoring and reporting prototype.

Python 3.10+, standard library for scoring/HTML/JSON; python-docx for Word output.
All scoring and interpretation rules are supplied by the configuration author.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
from copy import deepcopy
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

VERSION = '0.1.1'
METHODS = {'sum', 'mean', 'weighted_sum', 'weighted_mean'}
IDENTIFIER = re.compile(r'^[A-Za-z][A-Za-z0-9_]*$')
TOKENS = {'score', 'band', 'answered', 'items'}


class ConfigurationError(ValueError):
    pass


class DataError(ValueError):
    pass


def number(value):
    if isinstance(value, bool):
        raise ValueError('Boolean values are not numeric scores.')
    try:
        result = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        raise ValueError(f'Not a numeric score: {value!r}') from None
    if not result.is_finite():
        raise ValueError('Scores must be finite.')
    return result


def key(value):
    if value is None:
        return ''
    text = str(value).strip()
    try:
        x = number(text)
        return format(x.normalize(), 'f')
    except ValueError:
        return text


def exact(value):
    return format(value.normalize(), 'f') if value else '0'


def shown(value, decimals):
    """Participant-facing score: rounded half up to `decimals` places, trailing zeros removed."""
    return exact(value.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP))


def known_keys(obj, allowed, location):
    extra = set(obj) - set(allowed)
    if extra:
        raise ConfigurationError(f'{location}: unknown fields {sorted(extra)}')


def required_text(obj, field, location):
    if not isinstance(obj.get(field), str) or not obj[field].strip():
        raise ConfigurationError(f'{location}: {field} must be a nonempty string.')


def identifier(value, location):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ConfigurationError(f'{location}: use a letter followed by letters, digits or underscores.')


def check_template(text):
    if not isinstance(text, str):
        raise ConfigurationError('Band text must be a string.')
    found = re.findall(r'\{\{([a-z_]+)\}\}', text)
    rest = re.sub(r'\{\{([a-z_]+)\}\}', '', text)
    if set(found) - TOKENS or '{{' in rest or '}}' in rest:
        raise ConfigurationError('Templates allow only {{score}}, {{band}}, {{answered}} and {{items}}.')


def load_config(path):
    def unique_pairs(pairs):
        out = {}
        for k, v in pairs:
            if k in out:
                raise ConfigurationError(f'Duplicate JSON key: {k}')
            out[k] = v
        return out
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique_pairs)


class ReportEngine:
    def __init__(self, config):
        self.config = deepcopy(config)
        self.items = {}
        self.scales = []
        try:
            self._compile()
        except ConfigurationError:
            raise
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            raise ConfigurationError(str(exc)) from exc
        canonical = json.dumps(self.config, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
        self.config_sha256 = hashlib.sha256(canonical.encode()).hexdigest()

    def _compile(self):
        c = self.config
        known_keys(c, {'schema_version', 'questionnaire_id', 'title', 'instrument_version',
                      'scoring_reference', 'id_column', 'introduction', 'missing_codes',
                      'eligibility', 'items', 'scales', 'sections'}, 'configuration')
        if c.get('schema_version') != '1.0':
            raise ConfigurationError('schema_version must be 1.0.')
        for f in ('questionnaire_id', 'title', 'instrument_version', 'scoring_reference', 'id_column'):
            required_text(c, f, 'configuration')
        identifier(c['questionnaire_id'], 'questionnaire_id')
        if not isinstance(c.get('introduction', ''), str):
            raise ConfigurationError('introduction must be text.')
        missing = c.get('missing_codes', ['', None, 'NA'])
        if not isinstance(missing, list):
            raise ConfigurationError('missing_codes must be a list.')
        self.missing = {key(x) for x in missing}
        if not isinstance(c.get('items'), list) or not c['items']:
            raise ConfigurationError('At least one item is required.')
        used_columns = set()
        for item in c['items']:
            known_keys(item, {'id', 'column', 'min', 'max', 'reverse', 'allow_decimal', 'recode'}, 'item')
            identifier(item.get('id'), 'item id')
            required_text(item, 'column', 'item')
            iid = item['id']
            if iid in self.items or item['column'] in used_columns or item['column'] == c['id_column']:
                raise ConfigurationError('Item ids and item columns must be unique and distinct from id_column.')
            lo, hi = number(item['min']), number(item['max'])
            if lo > hi:
                raise ConfigurationError(f'{iid}: min exceeds max.')
            for f in ('reverse', 'allow_decimal'):
                if f in item and not isinstance(item[f], bool):
                    raise ConfigurationError(f'{iid}: {f} must be boolean.')
            recode = item.get('recode')
            if recode is not None:
                if not isinstance(recode, dict) or not recode:
                    raise ConfigurationError(f'{iid}: recode must be a nonempty object.')
                mapped = {key(k): number(v) for k, v in recode.items()}
                if len(mapped) != len(recode) or self.missing.intersection(mapped):
                    raise ConfigurationError(f'{iid}: duplicate or missing response code in recode.')
                if any(v < lo or v > hi for v in mapped.values()):
                    raise ConfigurationError(f'{iid}: recoded value outside item bounds.')
                if not item.get('allow_decimal', False) and any(v != v.to_integral_value() for v in mapped.values()):
                    raise ConfigurationError(f'{iid}: fractional recoding requires allow_decimal.')
            else:
                mapped = None
                for m in self.missing:
                    try:
                        x = number(m)
                    except ValueError:
                        continue
                    if lo <= x <= hi and (item.get('allow_decimal', False) or x == x.to_integral_value()):
                        raise ConfigurationError(f'{iid}: missing code {m} overlaps a valid response.')
            self.items[iid] = dict(source=item, lo=lo, hi=hi, recode=mapped)
            used_columns.add(item['column'])
        self.eligibility = c.get('eligibility', [])
        if not isinstance(self.eligibility, list):
            raise ConfigurationError('eligibility must be a list.')
        for e in self.eligibility:
            known_keys(e, {'column', 'equals', 'reason'}, 'eligibility')
            for f in ('column', 'reason'):
                required_text(e, f, 'eligibility')
            if 'equals' not in e:
                raise ConfigurationError('Eligibility requires equals.')
        if not isinstance(c.get('scales'), list) or not c['scales']:
            raise ConfigurationError('At least one scale is required.')
        ids = set()
        for s in c['scales']:
            known_keys(s, {'id', 'label', 'items', 'method', 'weights', 'missing_policy',
                          'multiplier', 'offset', 'bands', 'interpretation_reference', 'display_decimals'}, 'scale')
            identifier(s.get('id'), 'scale id')
            required_text(s, 'label', 'scale')
            if s['id'] in ids:
                raise ConfigurationError('Duplicate scale id.')
            ids.add(s['id'])
            if not isinstance(s.get('items'), list) or not s['items'] or len(s['items']) != len(set(s['items'])):
                raise ConfigurationError('Scale items must be a nonempty unique list.')
            if set(s['items']) - set(self.items):
                raise ConfigurationError('Scale references an undefined item.')
            method = s.get('method')
            if method not in METHODS:
                raise ConfigurationError(f'Unknown scoring method: {method}')
            weights = s.get('weights', {})
            if not isinstance(weights, dict) or set(weights) - set(s['items']):
                raise ConfigurationError('Weights reference an undefined scale item.')
            if weights and not method.startswith('weighted_'):
                raise ConfigurationError('Use a weighted method when supplying weights.')
            w = {i: number(weights.get(i, 1)) for i in s['items']}
            if any(x <= 0 for x in w.values()):
                raise ConfigurationError('Weights must be positive.')
            mp = s.get('missing_policy', {'method': 'complete'})
            known_keys(mp, {'method', 'minimum_answered', 'justification'}, 'missing_policy')
            if mp.get('method') not in {'complete', 'prorate'}:
                raise ConfigurationError('Missing policy must be complete or prorate.')
            n = len(s['items'])
            minimum = n
            if mp['method'] == 'prorate':
                minimum = mp.get('minimum_answered')
                if isinstance(minimum, bool) or not isinstance(minimum, int) or not 1 <= minimum <= n:
                    raise ConfigurationError('Proration requires a valid minimum_answered.')
                required_text(mp, 'justification', 'proration')
                bounds = {(self.items[i]['lo'], self.items[i]['hi']) for i in s['items']}
                if len(bounds) != 1:
                    raise ConfigurationError('This prototype prorates only items with identical scored bounds.')
            elif 'minimum_answered' in mp or 'justification' in mp:
                raise ConfigurationError('Complete scoring does not accept proration settings.')
            decimals = s.get('display_decimals', 2)
            if isinstance(decimals, bool) or not isinstance(decimals, int) or not 0 <= decimals <= 6:
                raise ConfigurationError('display_decimals must be an integer from 0 to 6.')
            mult, offset = number(s.get('multiplier', 1)), number(s.get('offset', 0))
            if mult <= 0:
                raise ConfigurationError('multiplier must be positive.')
            lower = sum(self.items[i]['lo'] * w[i] for i in s['items'])
            upper = sum(self.items[i]['hi'] * w[i] for i in s['items'])
            if method.endswith('mean'):
                lower /= sum(w.values()); upper /= sum(w.values())
            lower, upper = lower * mult + offset, upper * mult + offset
            bands = []
            source_bands = s.get('bands', [])
            if not isinstance(source_bands, list):
                raise ConfigurationError('bands must be a list.')
            if source_bands:
                required_text(s, 'interpretation_reference', 'scale with bands')
            seen_bands = set()
            for j, b in enumerate(source_bands):
                known_keys(b, {'id', 'label', 'lower', 'upper', 'upper_inclusive', 'text', 'hold'}, 'band')
                identifier(b.get('id'), 'band id'); required_text(b, 'label', 'band')
                if b['id'] in seen_bands:
                    raise ConfigurationError('Band ids must be unique within a scale.')
                seen_bands.add(b['id'])
                bl, bu = number(b['lower']), number(b['upper'])
                last = j == len(source_bands) - 1
                if not isinstance(b.get('upper_inclusive', False), bool) or not isinstance(b.get('hold', False), bool):
                    raise ConfigurationError('Band flags must be boolean.')
                if bl >= bu or b.get('upper_inclusive', False) != last:
                    raise ConfigurationError('Only the final band must include its upper boundary.')
                if j == 0 and bl != lower or bands and bands[-1]['upper'] != bl:
                    raise ConfigurationError('Bands must cover the score range without gaps or overlap, in ascending order.')
                check_template(b.get('text', ''))
                bands.append(dict(source=b, lower=bl, upper=bu))
            if bands and bands[-1]['upper'] != upper:
                raise ConfigurationError('Bands do not cover the maximum score.')
            self.scales.append(dict(source=s, weights=w, minimum=minimum, mult=mult, offset=offset, decimals=decimals,
                                    bands=bands, lower=lower, upper=upper, missing_policy=mp['method']))
        self.sections = c.get('sections', [])
        if not isinstance(self.sections, list):
            raise ConfigurationError('sections must be a list.')
        seen_sections = set()
        def condition_check(node):
            if not isinstance(node, dict):
                raise ConfigurationError('A condition must be an object.')
            if set(node) in ({'all'}, {'any'}):
                nodes = next(iter(node.values()))
                if not isinstance(nodes, list) or not nodes:
                    raise ConfigurationError('all/any conditions require a nonempty list.')
                for n in nodes: condition_check(n)
            elif set(node) == {'not'}:
                condition_check(node['not'])
            else:
                known_keys(node, {'scale', 'item', 'op', 'value'}, 'condition')
                if ('scale' in node) == ('item' in node):
                    raise ConfigurationError('A condition names exactly one scale or item.')
                if node.get('scale') not in ids and node.get('item') not in self.items:
                    raise ConfigurationError('Condition references an undefined scale/item.')
                if node.get('op') not in {'eq','ne','lt','le','gt','ge'}:
                    raise ConfigurationError('Unknown comparison operator.')
                number(node['value'])
        for section in self.sections:
            known_keys(section, {'id','title','text','source','when'}, 'section')
            identifier(section.get('id'),'section id')
            if section['id'] in seen_sections: raise ConfigurationError('Duplicate section id.')
            seen_sections.add(section['id'])
            for f in ('title','text','source'): required_text(section,f,'section')
            if '{{' in section['text'] or '}}' in section['text']:
                raise ConfigurationError('Section text is literal; numeric scores appear in the score table.')
            if 'when' in section: condition_check(section['when'])

    def score(self, row):
        c = self.config
        needed = {c['id_column']} | {i['source']['column'] for i in self.items.values()} | {e['column'] for e in self.eligibility}
        absent = needed - set(row)
        if absent:
            raise DataError(f'Missing input columns: {sorted(absent)}')
        pid = '' if row[c['id_column']] is None else str(row[c['id_column']]).strip()
        if not pid or len(pid) > 128 or any(ord(x) < 32 for x in pid):
            raise DataError('Participant id must be printable, nonempty and at most 128 characters.')
        reasons = [e['reason'] for e in self.eligibility if key(row[e['column']]) != key(e['equals'])]
        trace = {}
        for iid, item in self.items.items():
            spec = item['source']; raw = row[spec['column']]; token = key(raw)
            t = dict(column=spec['column'], raw=None if raw is None else str(raw), status='missing')
            if token not in self.missing:
                try:
                    if len(token) > 256:
                        raise ValueError('Response token too long.')
                    value = item['recode'][token] if item['recode'] is not None else number(token)
                    if not item['lo'] <= value <= item['hi']:
                        raise ValueError('Response outside configured bounds.')
                    if not spec.get('allow_decimal', False) and value != value.to_integral_value():
                        raise ValueError('Fractional response is not allowed for this item.')
                    scored = item['lo'] + item['hi'] - value if spec.get('reverse', False) else value
                    t.update(status='valid', mapped=exact(value), scored=exact(scored), reversed=spec.get('reverse', False))
                except (ValueError, KeyError) as exc:
                    t.update(status='invalid', reason='Unknown response code.' if isinstance(exc, KeyError) else str(exc))
                    reasons.append(f'Invalid response in {iid}: {t["reason"]}')
            trace[iid] = t
        results = []
        hold = False
        for scale in self.scales:
            s = scale['source']; use = s['items']; w = scale['weights']
            good = [i for i in use if trace[i]['status'] == 'valid']
            invalid = [i for i in use if trace[i]['status'] == 'invalid']
            r = dict(id=s['id'], label=s['label'], method=s['method'], item_ids=use,
                     answered=len(good), expected=len(use), missing=[i for i in use if trace[i]['status'] == 'missing'],
                     invalid=invalid, status='unscored', score=None, score_exact=None, score_display=None, band=None, text='', prorated=False)
            if invalid:
                r['reason'] = 'Invalid item response; scale withheld.'
            elif len(good) < scale['minimum']:
                r['reason'] = 'Too few answered items for the configured scoring rule.'
            else:
                numerator = sum(number(trace[i]['scored']) * w[i] for i in good)
                denominator = sum(w[i] for i in good)
                raw_score = numerator / denominator if s['method'].endswith('mean') else numerator
                if len(good) < len(use):
                    if not s['method'].endswith('mean'):
                        raw_score *= sum(w.values()) / denominator
                    r['prorated'] = True
                    r['proration_justification'] = s['missing_policy']['justification']
                value = raw_score * scale['mult'] + scale['offset']
                r.update(status='scored', raw_score_exact=exact(raw_score), score=float(value), score_exact=exact(value),
                         score_display=shown(value, scale['decimals']))
                for b in scale['bands']:
                    bs = b['source']
                    if value >= b['lower'] and (value < b['upper'] or bs['upper_inclusive'] and value == b['upper']):
                        r['band'] = dict(id=bs['id'], label=bs['label'], source=s['interpretation_reference'])
                        context = dict(score=r['score_display'], band=bs['label'], answered=str(len(good)), items=str(len(use)))
                        r['text'] = re.sub(r'\{\{([a-z_]+)\}\}', lambda m: context[m[1]], bs.get('text', ''))
                        hold = hold or bs.get('hold', False)
                        break
                if scale['bands'] and r['band'] is None:
                    raise DataError('A computed score lies outside the configured bands.')
            results.append(r)
        scored = sum(r['status'] == 'scored' for r in results)
        status = 'blocked' if reasons else 'held_for_review' if hold else 'unscored' if scored == 0 else 'partial' if scored < len(results) else 'ready'
        by_id = {r['id']: r for r in results}
        def evaluate(node):
            if 'all' in node or 'any' in node:
                is_all = 'all' in node
                values = [evaluate(n) for n in node['all' if is_all else 'any']]
                if is_all and False in values: return False
                if not is_all and True in values: return True
                return None if None in values else is_all
            if 'not' in node:
                value = evaluate(node['not']); return None if value is None else not value
            if 'scale' in node:
                s = by_id[node['scale']]
                value = number(s['score_exact']) if s['status']=='scored' else None
            else:
                t = trace[node['item']]
                value = number(t['scored']) if t['status']=='valid' else None
            if value is None: return None
            rhs = number(node['value'])
            return {'eq':value==rhs,'ne':value!=rhs,'lt':value<rhs,'le':value<=rhs,'gt':value>rhs,'ge':value>=rhs}[node['op']]
        sections, section_trace = [], []
        for s in self.sections:
            decision = evaluate(s['when']) if 'when' in s else True
            section_trace.append(dict(id=s['id'],decision='included' if decision is True else 'excluded' if decision is False else 'withheld_unknown',source=s['source']))
            if decision is True: sections.append({k:s[k] for k in ('id','title','text','source')})
        return dict(engine_version=VERSION, questionnaire_id=c['questionnaire_id'], instrument_version=c['instrument_version'],
                    config_sha256=self.config_sha256, participant_id=pid, title=c['title'],
                    introduction=c.get('introduction', ''), scoring_reference=c['scoring_reference'],
                    status=status, reasons=reasons, scales=results, item_trace=trace,sections=sections,section_trace=section_trace)


def score_rows(engine, rows):
    results = [engine.score(r) for r in rows]
    ids = [r['participant_id'] for r in results]
    if len(ids) != len(set(ids)):
        raise DataError('Duplicate participant ids; no reports should be written.')
    return results


def render_html(report):
    if report['status'] not in {'ready', 'partial'}:
        raise DataError(f'Report is {report["status"]}; release is withheld.')
    esc = lambda x: html.escape(str(x), quote=True)
    rows, paragraphs = [], []
    for s in report['scales']:
        score = s['score_display'] if s['status'] == 'scored' else 'Not scored'
        band = s['band']['label'] if s['band'] else 'Not assigned'
        coverage = f'{s["answered"]} / {s["expected"]}' + ('; prorated' if s['prorated'] else '')
        rows.append('<tr>' + ''.join('<td>' + esc(x) + '</td>' for x in (s['label'], score, band, coverage)) + '</tr>')
        paragraphs.append('<h2>' + esc(s['label']) + '</h2><p>' + esc(s['text'] if s['status'] == 'scored' else s['reason']) + '</p>')
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><title>' + esc(report['title']) + '</title>'
            '<style>body{font:17px/1.5 Arial,sans-serif;max-width:860px;margin:40px auto;padding:0 24px;color:#171717}h1{font-size:28px}h2{font-size:21px}table{border-collapse:collapse;width:100%}th,td{border:1px solid #d9d9d9;padding:10px;text-align:left}th{background:#edf1f4}.note{font-size:14px}</style>'
            '<h1>' + esc(report['title']) + '</h1><p>Participant ' + esc(report['participant_id']) + '</p><p>' + esc(report['introduction']) + '</p>'
            '<table><thead><tr><th>Scale</th><th>Score</th><th>Band</th><th>Answered items</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table>'
            + ''.join(paragraphs) + ''.join('<h2>'+esc(s['title'])+'</h2><p>'+esc(s['text'])+'</p>' for s in report['sections'])
            + '<p class="note">Scoring reference: ' + esc(report['scoring_reference']) + '</p><p class="note">Instrument version: '
            + esc(report['instrument_version']) + '; engine ' + VERSION + '; configuration SHA-256 ' + esc(report['config_sha256']) + '</p></html>')


def render_docx(report, path):
    # Import only when Word export is requested; scoring itself has no package dependencies.
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    if report['status'] not in {'ready', 'partial'}:
        raise DataError(f'Report is {report["status"]}; release is withheld.')
    d = Document(); sec = d.sections[0]
    sec.page_width, sec.page_height = Inches(8.5), Inches(11)
    sec.top_margin = sec.bottom_margin = Inches(.8)
    sec.left_margin = sec.right_margin = Inches(.8)
    for name in ('Normal', 'Title', 'Heading 1', 'Heading 2'):
        st = d.styles[name]; st.font.name = 'Arial'; st.font.color.rgb = RGBColor(0,0,0)
        for border in list(st.element.findall('.//' + qn('w:pBdr'))):
            border.getparent().remove(border)
    d.styles['Normal'].font.size = Pt(11)
    d.styles['Normal'].paragraph_format.space_after = Pt(8)
    d.styles['Title'].font.size = Pt(21)
    d.styles['Heading 2'].font.size = Pt(12)
    d.add_heading(report['title'], 0)
    d.add_paragraph('Participant ' + report['participant_id'])
    d.add_paragraph(report['introduction'])
    table = d.add_table(rows=1, cols=4); table.autofit = False
    widths = [2.2, 1.0, 1.8, 1.9]
    for col, width in zip(table.columns, widths): col.width = Inches(width)
    for c, t in zip(table.rows[0].cells, ['Scale', 'Score', 'Band', 'Answered items']): c.text=t
    for s in report['scales']:
        vals = [s['label'], s['score_display'] if s['status']=='scored' else 'Not scored',
                s['band']['label'] if s['band'] else 'Not assigned', f'{s["answered"]} / {s["expected"]}' + ('; prorated' if s['prorated'] else '')]
        for c, t in zip(table.add_row().cells, vals): c.text=str(t)
    borders=OxmlElement('w:tblBorders')
    for edge in ['top','left','bottom','right','insideH','insideV']:
        e=OxmlElement('w:'+edge);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'D9D9D9');borders.append(e)
    table._tbl.tblPr.append(borders)
    for row_no,row in enumerate(table.rows):
        pr=row._tr.get_or_add_trPr();pr.append(OxmlElement('w:cantSplit'))
        if row_no==0:pr.append(OxmlElement('w:tblHeader'))
        for c,w in zip(row.cells,widths):
            c.width=Inches(w)
            if row_no==0:
                sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'EDF1F4');c._tc.get_or_add_tcPr().append(sh)
            margins=OxmlElement('w:tcMar')
            for edge in ['top','left','bottom','right']:
                v=OxmlElement('w:'+edge);v.set(qn('w:w'),'90');v.set(qn('w:type'),'dxa');margins.append(v)
            c._tc.get_or_add_tcPr().append(margins)
            for p in c.paragraphs:
                p.paragraph_format.space_after=Pt(3)
                for run in p.runs: run.font.size=Pt(10);run.bold=row_no==0
    d.add_paragraph()
    for s in report['scales']:
        d.add_heading(s['label'],2)
        d.add_paragraph(s['text'] if s['status']=='scored' else s['reason'])
        if s['prorated']:d.add_paragraph('Proration rule: ' + s['proration_justification'])
    for s in report['sections']:
        d.add_heading(s['title'],2);d.add_paragraph(s['text'])
    d.add_paragraph('Scoring reference: ' + report['scoring_reference'])
    p=d.add_paragraph('Instrument version ' + report['instrument_version'] + '; engine ' + VERSION)
    for run in p.runs:run.font.size=Pt(9)
    p=d.add_paragraph('Configuration SHA-256: ' + report['config_sha256'])
    for run in p.runs:run.font.size=Pt(8)
    d.core_properties.author='';d.core_properties.title=report['title']
    d.save(path)


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--config',required=True);ap.add_argument('--data',required=True)
    ap.add_argument('--out',required=True);ap.add_argument('--docx',action='store_true')
    args=ap.parse_args(argv)
    engine=ReportEngine(load_config(args.config)); data=Path(args.data).read_bytes()
    with Path(args.data).open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if reader.fieldnames is None or len(reader.fieldnames)!=len(set(reader.fieldnames)):
            raise DataError('CSV headers must be present and unique.')
        rows=list(reader)
        if any(None in r for r in rows):raise DataError('A CSV row has extra fields.')
        if any(v is None for r in rows for v in r.values()):
            raise DataError('A CSV row has fewer fields than the header; no reports were written.')
    results=score_rows(engine,rows)
    out=Path(args.out)
    if out.exists() and any(out.iterdir()):raise DataError('Output directory is not empty; choose a new directory.')
    out.mkdir(parents=True,exist_ok=True)
    counts={}
    for r in results:
        counts[r['status']]=counts.get(r['status'],0)+1
        stem='report_'+hashlib.sha256(r['participant_id'].encode()).hexdigest()[:16]
        r['output_stem']=stem
        (out/(stem+'.json')).write_text(json.dumps(r,indent=2,ensure_ascii=False),encoding='utf-8')
        if r['status'] in {'ready','partial'}:
            (out/(stem+'.html')).write_text(render_html(r),encoding='utf-8')
            if args.docx:render_docx(r,out/(stem+'.docx'))
    manifest=dict(engine_version=VERSION,config_sha256=engine.config_sha256,
                  input_sha256=hashlib.sha256(data).hexdigest(),records=len(results),status_counts=counts,
                  outputs=[dict(participant_id=r['participant_id'],status=r['status'],stem=r['output_stem']) for r in results])
    (out/'run_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest,indent=2))


if __name__=='__main__':
    main()
