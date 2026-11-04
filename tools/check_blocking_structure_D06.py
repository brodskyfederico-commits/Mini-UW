"""D06: replay the documented distinction between input, calculation and release gates.

All edits are disposable, in-memory synthetic fault probes. No registry is refreshed.
This checker does not implement a financial rule or an agent runtime.
"""
import argparse
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import sys

from check_reference_package import PackageError, local_file, require
from check_dependency_structure_D05 import source_function, resolve_pointer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
DIRECTORY = 'docs/current-structure/'
SNAPSHOT = DIRECTORY + 'MiniUW_Bloqueos_D06.json'
CSV = DIRECTORY + 'MiniUW_Bloqueos_D06.csv'
RECORD = DIRECTORY + 'D06-structural-validation.json'
CASE = 'templates/miniuw-v1-policy-renewal-case.json'
BASE_CHAIN = ['/scheduled_case_utf8', '/base_case_utf8']
POLICY_CHAIN = ['/policy_books_utf8/0']
REGISTRY_CHAIN = ['/registry_utf8']
WITHDRAWN_MONEY = ['1400.0000', '778.0000', '-622.0000', '578.0000']


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def edit(raw, operation):
    """Apply one explicit locator edit without changing the other embedded sources."""
    steps = operation['embedded_json_pointers']
    pointer = operation['final_pointer']
    def walk(source, remaining):
        value = json.loads(source)
        if remaining:
            target = remaining[0]
            old = resolve_pointer(value, target)
            require(type(old) is str, 'explicit embedded UTF-8 source required')
            replacement = walk(old.encode(), remaining[1:]).decode()
        else:
            target = pointer
            old = resolve_pointer(value, target)
            replacement = (old + operation['value'] if operation['operation'] == 'append_UTF8'
                           else copy.deepcopy(operation['value']))
        parent_pointer, key = target.rsplit('/', 1)
        parent = resolve_pointer(value, parent_pointer)
        key = key.replace('~1', '/').replace('~0', '~')
        require(operation['operation'] in ('replace', 'append_UTF8'), 'supported fault probe operation required')
        if isinstance(parent, list):
            parent[int(key)] = replacement
        else:
            require(key in parent, 'fault probe must address an existing source slot')
            parent[key] = replacement
        return encoded(value)
    return walk(raw, steps)


def op(chain, pointer, value, operation='replace'):
    return dict(embedded_json_pointers=chain, final_pointer=pointer,
                operation=operation, value=value)


def definitions(raw):
    outer = json.loads(raw)
    base = json.loads(json.loads(outer['scheduled_case_utf8'])['base_case_utf8'])
    original_index = next(i for i, row in enumerate(base['original_inputs']) if row['field_id'] == 'INPUT_C7')
    q = lambda n: dict(numerator=str(n), denominator='1')
    def scenario(sid, label, operations, expected, blockers=(), pdf=False, raw_fault=None):
        return dict(scenario_id=sid, label=label, operations=operations,
                    expected_outcome=expected, required_blocker_fragments=list(blockers),
                    render_probe=pdf, raw_fault=raw_fault,
                    synthetic_evidence_refresh=False)
    return [
        scenario('D06-01', 'Perfil calculable con 54 campos y criterios pendientes', [], 'current_projection_pending_decision', pdf=True),
        scenario('D06-02', 'Valor original contradice la fuente vinculada', [op(BASE_CHAIN, '/original_inputs/'+str(original_index)+'/value', 'per_area_per_month')], 'current_figures_withdrawn', ['original_input_and_recipe_conflict']),
        scenario('D06-03', 'Pago de principal operativo ausente', [op(BASE_CHAIN, '/recipe/operating_periods/0/cash_source/amounts/debt_principal_payment/value', None)], 'current_figures_withdrawn', ['operating_cash:SYNTHETIC-hold-1:/amounts/debt_principal_payment:amount_missing', 'scheduled_parent_current_projection_unavailable']),
        scenario('D06-04', 'Evidencia de póliza vencida en el corte expreso', [op(REGISTRY_CHAIN, '/evidence/42/valid_until', outer['as_of_UTC'])], 'current_figures_withdrawn', ['policy_renewal_sources_not_current', 'evidence_expired'], pdf=True),
        scenario('D06-05', 'Revisión declarada pendiente', [op(REGISTRY_CHAIN, '/evidence/42/review_status', 'pending')], 'current_figures_withdrawn', ['synthetic_review_pending']),
        scenario('D06-06', 'Fuente declarada sustituida', [op(REGISTRY_CHAIN, '/evidence/42/superseded_by_sha256', '1'*64)], 'current_figures_withdrawn', ['evidence_superseded']),
        scenario('D06-07', 'Prima ausente conserva ausencia', [op(POLICY_CHAIN, '/policies/0/premium', None)], 'current_figures_withdrawn', ['premium_missing_or_negative']),
        scenario('D06-08', 'Cuotas 6 y 4 conservan total pero contradicen grupos 5 y 15', [op(POLICY_CHAIN, '/policies/0/installments/0/amount', q(6)), op(POLICY_CHAIN, '/policies/0/installments/1/amount', q(4))], 'current_figures_withdrawn', ['group_sum_differs_from_exact_aggregate_installment']),
        scenario('D06-09', 'Mismos importes con bytes de póliza distintos', [op([], '/policy_books_utf8/0', '\n', 'append_UTF8')], 'current_figures_withdrawn', ['complete_policy_renewal_source_inventory_mismatch'], pdf=True),
        scenario('D06-10', 'Evidencia del padre vencida aunque el registro exterior se conserve', [op(['/scheduled_case_utf8', '/registry_utf8'], '/evidence/40/valid_until', outer['as_of_UTC'])], 'current_figures_withdrawn', ['scheduled_expense_sources_not_current', 'evidence_expired']),
        scenario('D06-11', 'Esquema JSON con clave duplicada', [], 'input_rejected', raw_fault='duplicate_outer_schema'),
        scenario('D06-12', 'Otro escenario solicitado sin un recorrido compatible', [op(BASE_CHAIN, '/required_scenarios', base['required_scenarios']+['SYNTHETIC-unconfigured-downside'])], 'current_figures_withdrawn', ['requested_scenario_inventory_outside_single_synthetic_profile']),
    ]


def probe_source(raw, definition):
    if definition['raw_fault'] == 'duplicate_outer_schema':
        return b'{"schema":"miniuw.synthetic-v1-policy-renewal-case.v1",' + raw.lstrip()[1:]
    result = raw
    for operation in definition['operations']:
        result = edit(result, operation)
    return result


def history(rows):
    result = []
    for row in rows:
        p = json.loads(row['payload_json'])
        result.append(dict(run_sha256=row['sha256'], state=p['state'],
                           computed_totals_retained=p['totals'] is not None))
    return result


def observe(raw, definition):
    from miniuw_foundation.drafts import ValidationError
    from miniuw_foundation.policy_renewal_case import assemble_policy_renewal_case
    from miniuw_foundation.policy_renewal_artifacts import render_policy_renewal_report
    from pypdf import PdfReader
    source = probe_source(raw, definition)
    result = dict(scenario_id=definition['scenario_id'], source_sha256=sha(source))
    try:
        run = assemble_policy_renewal_case(source)
    except ValidationError as error:
        require(definition['expected_outcome'] == 'input_rejected', 'unexpected rejected fault probe')
        result.update(outcome='input_rejected', exception_type=type(error).__name__, reason=str(error),
                      run_sha256=None, report=None, decision=None, current_figures_available=False)
        return result
    require(definition['expected_outcome'] != 'input_rejected', 'malformed source was accepted')
    p = run.payload
    present = p['current_project_return_story'] is not None
    expected_present = definition['expected_outcome'] == 'current_projection_pending_decision'
    require(present == expected_present, 'current projection availability differs from documented gate')
    require(p['decision'] == 'PENDING', 'real decision must remain PENDING')
    flags = ('full_financial_model_completed', 'full_input_sheet_adapter_completed',
             'personal_return_verified', 'independent_financial_audit_completed',
             'professional_review_authenticated', 'financial_publication_authorized',
             'deployment_enabled', 'real_decisions_enabled')
    require(all(p[key] is False for key in flags), 'unsupported financial or operational release')
    serialized_blockers = json.dumps(p['blockers'], ensure_ascii=False)
    require(all(fragment in serialized_blockers for fragment in definition['required_blocker_fragments']),
            'documented primary blocker not observed')
    if not present:
        require(p['current_schedule_totals'] is None and p['current_policy_cost_totals'] is None,
                'partial current totals leaked through blocked route')
        require(all(m['value'] is None and m['comparison_state'] == 'PENDING' for m in p['metrics']),
                'current point metric/comparison leaked through blocked route')
    else:
        require(p['input_catalog_summary'] == dict(total=55, bound=1, pending=54), 'baseline field coverage changed')
        require(all(m['criterion']['source_ref'] is None for m in p['metrics']), 'fresh criteria unexpectedly filled')
    result.update(outcome=definition['expected_outcome'], run_sha256=run.sha256, state=p['state'],
                  decision=p['decision'], current_figures_available=present,
                  current_schedule_totals_available=p['current_schedule_totals'] is not None,
                  current_policy_totals_available=p['current_policy_cost_totals'] is not None,
                  metric_point_values_available=sum(m['value'] is not None for m in p['metrics']),
                  metric_states=[{key:m[key] for key in ('metric_id','value_state','comparison_state')} for m in p['metrics']],
                  input_catalog_summary=p['input_catalog_summary'], blockers=p['blockers'],
                  stage_evidence=p['stages'],
                  schedule_history=history(p['historical_schedule_runs']),
                  policy_history=history(p['historical_policy_runs']),
                  release_gates={key:p[key] for key in flags}, report=None)
    if definition['render_probe']:
        report = render_policy_renewal_report(source, run)
        reader = PdfReader(io.BytesIO(report.pdf_bytes))
        require(len(reader.pages) == 1, 'one-page synthetic report required')
        text = reader.pages[0].extract_text()
        require('PENDIENTE' in text and all(s['text'] in text for s in report.manifest['display_spans']),
                'required PDF decision/spans not recovered')
        require(all((token in text) == present for token in WITHDRAWN_MONEY),
                'current cash figures in PDF inconsistent with gate')
        result['report'] = dict(pdf_sha256=sha(report.pdf_bytes), text_sha256=sha(text.encode()),
                                manifest_sha256=report.manifest_sha256, page_count=1,
                                current_money_present=present, four_cash_tokens_checked=WITHDRAWN_MONEY)
    return result


def build_snapshot():
    raw = local_file(ROOT, CASE).read_bytes()
    scenarios = definitions(raw)
    observations = [observe(raw, definition) for definition in scenarios]
    require(local_file(ROOT, CASE).read_bytes() == raw, 'original synthetic source mutated')
    require(observe(raw, scenarios[0]) == observations[0], 'unchanged baseline did not reproduce after probes')
    require(all(h['computed_totals_retained'] for h in observations[8]['policy_history']),
            'same-money byte-change probe must preserve historical policy calculation')
    require(all(not h['computed_totals_retained'] for h in observations[6]['policy_history']),
            'missing premium must not be replaced with a computed zero')
    require(observations[1]['stage_evidence'] == [] and observations[11]['stage_evidence'] == [],
            'original conflict or unsupported scenario must block before financial projection')
    missing_cash_stages = observations[2]['stage_evidence']
    require(missing_cash_stages[-1]['stage'] == 'operating_cash:SYNTHETIC-hold-1'
            and missing_cash_stages[-1]['state'] == 'blocked'
            and all(row['stage'] != 'holding_cash' for row in missing_cash_stages),
            'missing cash input must stop the financial route at operating cash')
    functions = [('v1_case','run_v1_case'), ('v1_case','parse_v1_case'),
                 ('scheduled_expense_case','assemble_scheduled_expense_case'),
                 ('policy_renewal_case','assemble_policy_renewal_case'),
                 ('policy_renewal_case','parse_policy_renewal_case'),
                 ('insurance_renewals','reconcile_insurance_renewals'),
                 ('evidence_currency','evaluate_evidence_currency'),
                 ('policy_renewal_artifacts','render_policy_renewal_report')]
    locations = [source_function(ROOT, module, symbol) for module, symbol in functions]
    paths = {location['path'] for location in locations} | {
        'tools/check_blocking_structure_D06.py','tools/check_dependency_structure_D05.py',
        'src/miniuw_foundation/v1_projection.py','src/miniuw_foundation/v1_report.py',
        'docs/requirements-conflicts.md','docs/miniuw-v1-dot-bot-contracts.json',
        DIRECTORY+'MiniUW_Estructura_Vigente_D04.json',
        DIRECTORY+'MiniUW_Dependencias_D05.json'}
    return dict(snapshot_id='D06', technical_baseline='T95', registered_technical_unit_tests=1351,
                scope='Read-only structural gate demonstration on disposable synthetic faults; not financial acceptance or agent execution',
                base_case=dict(path=CASE, sha256=sha(raw)), scenarios=scenarios,
                observations=observations, function_locations=locations,
                source_versions=[dict(path=path,sha256=sha(local_file(ROOT,path).read_bytes())) for path in sorted(paths)],
                baseline_unchanged_and_replayed_after_probes=True,
                synthetic_evidence_refresh=False, original_field_runtime_mappings_pending=54,
                financial_model_complete=False, professional_review_authenticated=False,
                independent_financial_audit=False, deployment_enabled=False, real_decisions_enabled=False)


def flat_csv(snapshot):
    stream = io.StringIO(newline='')
    keys = ['scenario_id','trigger','source_edit_locators','outcome','decision','current_figures_available',
            'metric_point_values_available','primary_blocker_fragments','render_probe','run_sha256']
    writer = csv.DictWriter(stream, fieldnames=keys)
    writer.writeheader()
    for definition, observed in zip(snapshot['scenarios'],snapshot['observations']):
        writer.writerow(dict(scenario_id=definition['scenario_id'],trigger=definition['label'],
                             source_edit_locators=json.dumps(definition['operations'],ensure_ascii=False,sort_keys=True),
                             outcome=observed['outcome'],decision=observed['decision'] or 'sin corrida',
                             current_figures_available=observed['current_figures_available'],
                             metric_point_values_available=observed.get('metric_point_values_available','sin corrida'),
                             primary_blocker_fragments='; '.join(definition['required_blocker_fragments']),
                             render_probe=definition['render_probe'],run_sha256=observed['run_sha256'] or ''))
    return stream.getvalue().encode()


def validate(snapshot, expected):
    require(snapshot == expected, 'D06 definitions/locators/gates/evidence differ from actual source replay')


def negative_checks(snapshot, expected):
    mutations = [
        ('invented_PASS', lambda p:p['observations'][0].update(decision='PASS')),
        ('blocked_figures_exposed', lambda p:p['observations'][3].update(current_figures_available=True)),
        ('missing_scenario', lambda p:p['observations'].pop()),
        ('wrong_source_edit_locator', lambda p:p['scenarios'][1]['operations'][0].update(final_pointer='/missing')),
        ('unsupported_deployment', lambda p:p.update(deployment_enabled=True)),
    ]
    rejected = []
    for name, mutate in mutations:
        candidate = copy.deepcopy(snapshot)
        mutate(candidate)
        try:
            validate(candidate, expected)
        except PackageError:
            rejected.append(name)
        else:
            raise PackageError('altered D06 evidence accepted: '+name)
    return rejected


def validation_record(snapshot, rejected):
    outcomes = [row['outcome'] for row in snapshot['observations']]
    return dict(snapshot='D06',status='passed_scoped_gate_and_replay_check',
                checker_sha256=sha(Path(__file__).read_bytes()),
                scenarios_checked=len(outcomes),calculated_projection_pending_decision=outcomes.count('current_projection_pending_decision'),
                current_figures_withdrawn=outcomes.count('current_figures_withdrawn'),input_rejected=outcomes.count('input_rejected'),
                pdfs_replayed_and_text_checked=sum(row['report'] is not None for row in snapshot['observations']),
                source_hashes_checked=len(snapshot['source_versions'])+1,
                baseline_replayed_after_probes=True,negative_structural_cases_rejected=rejected,
                no_synthetic_registry_refresh=True,financial_validation_performed=False,
                professional_review_authenticated=False,independent_financial_audit=False,
                deployment_enabled=False,real_decisions_enabled=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--emit-snapshot', action='store_true')
    parser.add_argument('--emit-record', action='store_true')
    args = parser.parse_args()
    try:
        expected = build_snapshot()
        if args.emit_snapshot:
            print(json.dumps(expected, ensure_ascii=False, indent=2))
        else:
            snapshot = json.loads(local_file(ROOT,SNAPSHOT).read_bytes())
            validate(snapshot,expected)
            require(local_file(ROOT,CSV).read_bytes() == flat_csv(snapshot), 'D06 CSV differs from replayed matrix')
            result = validation_record(snapshot,negative_checks(snapshot,expected))
            if not args.emit_record:
                require(json.loads(local_file(ROOT,RECORD).read_bytes()) == result, 'D06 validation record differs')
            print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError,OSError,KeyError,TypeError,IndexError,StopIteration) as error:
        print(json.dumps(dict(status='failed',reason=str(error),financial_validation_performed=False)))
        sys.exit(1)
