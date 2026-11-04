"""Read-only source-first replay of the published T97 eight-artifact example."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.investor_output_artifacts import audit_investor_output_directory, recover_investor_output_bundle
from miniuw_foundation.scheduled_expense_artifacts import read_artifacts

EXAMPLE = ROOT/'docs/review/miniuw-v1-investor-package-example'
RECORD = ROOT/'docs/review/investor-output-package-validation-T97.json'
sha = lambda raw:hashlib.sha256(raw).hexdigest()


def verify():
    audit = audit_investor_output_directory(EXAMPLE)
    files = read_artifacts(EXAMPLE)
    recovered = recover_investor_output_bundle(files['execution-evidence.json'])
    if (recovered.case_raw != files['case.json']
            or (recovered.run.payload_json+'\n').encode() != files['results.json']
            or recovered.report.pdf_bytes != files['MiniUW_v1_Resumen.pdf']
            or (recovered.report.manifest_json+'\n').encode() != files['report-manifest.json']):
        raise ValidationError('published investor example differs from portable recovery')
    return dict(component='T97',status='passed_source_first_package_and_report_replay',
                files_verified=audit['files_verified'],page_count=1,
                case_sha256=sha(files['case.json']),run_sha256=recovered.run.sha256,
                pdf_sha256=sha(recovered.report.pdf_bytes),manifest_sha256=recovered.report.manifest_sha256,
                bundle_sha256=sha(files['execution-evidence.json']),
                source_versions=[dict(path=path,sha256=sha((ROOT/path).read_bytes())) for path in (
                    'src/miniuw_foundation/investor_output_artifacts.py','tools/investor_miniuw_v1.py',
                    'tools/check_investor_package_T97.py','docs/technical-implementation-T97.md')],
                decision='PENDING',independent_financial_audit=False,financial_publication_authorized=False,
                deployment_enabled=False,real_decisions_enabled=False)


if __name__=='__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--emit-record',action='store_true'); args = parser.parse_args()
    try:
        result = verify()
        if not args.emit_record and json.loads(RECORD.read_bytes()) != result:
            raise ValidationError('stored T97 example verification differs')
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (ValueError,OSError,KeyError,TypeError) as error:
        print(json.dumps(dict(status='failed',reason=str(error),financial_validation_performed=False)))
        raise SystemExit(1)
