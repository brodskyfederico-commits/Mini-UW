"""T108 local synthetic opening/operating/stocks/sale/return source replay."""
from pathlib import Path
import argparse,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.settled_case_artifacts import write_settled_case_artifacts,audit_settled_case_directory


def main():
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
    r=sub.add_parser('run');r.add_argument('case');r.add_argument('--output',required=True)
    a=sub.add_parser('audit');a.add_argument('directory');args=parser.parse_args()
    try:result=audit_settled_case_directory(args.directory)if args.command=='audit'else write_settled_case_artifacts(Path(args.case).read_bytes(),args.output)
    except(ValidationError,ValueError,OSError)as error:
        print(json.dumps(dict(status='blocked',reason=str(error),decision='PENDING',real_decisions_enabled=False)),file=sys.stderr);return 2
    print(json.dumps(result));return 0


if __name__=='__main__':raise SystemExit(main())
