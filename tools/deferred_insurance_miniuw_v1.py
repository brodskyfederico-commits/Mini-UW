"""Run/audit an explicit synthetic nominal settlement plan, without moving cash."""
from pathlib import Path
import argparse,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from miniuw_foundation.deferred_insurance_artifacts import write_deferred_insurance_artifacts,audit_deferred_insurance_directory
from miniuw_foundation.drafts import ValidationError


def main():
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
    r=sub.add_parser('run');r.add_argument('source');r.add_argument('--output',required=True)
    a=sub.add_parser('audit');a.add_argument('directory');args=parser.parse_args()
    try:
        result=(audit_deferred_insurance_directory(args.directory)if args.command=='audit'else
            write_deferred_insurance_artifacts(Path(args.source).read_bytes(),args.output))
    except(ValidationError,ValueError,OSError)as error:
        print(json.dumps(dict(status='blocked',reason=str(error),decision='PENDING',full_case_financial_integration_completed=False)),file=sys.stderr);return 2
    print(json.dumps(result));return 0


if __name__=='__main__':raise SystemExit(main())
