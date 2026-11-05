"""Run/audit supplied synthetic plan, sale closing and terminal binding locally."""
from pathlib import Path
import argparse,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from miniuw_foundation.insurance_terminal_artifacts import write_insurance_terminal_artifacts,audit_insurance_terminal_directory
from miniuw_foundation.drafts import ValidationError


def main():
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
    r=sub.add_parser('run');r.add_argument('plan');r.add_argument('closing');r.add_argument('binding');r.add_argument('--output',required=True)
    a=sub.add_parser('audit');a.add_argument('directory');args=parser.parse_args()
    try:
        result=(audit_insurance_terminal_directory(args.directory)if args.command=='audit'else
            write_insurance_terminal_artifacts(Path(args.plan).read_bytes(),Path(args.closing).read_bytes(),Path(args.binding).read_bytes(),args.output))
    except(ValidationError,ValueError,OSError)as error:
        print(json.dumps(dict(status='blocked',reason=str(error),decision='PENDING',full_operating_sale_return_integration_completed=False)),file=sys.stderr);return 2
    print(json.dumps(result));return 0


if __name__=='__main__':raise SystemExit(main())
