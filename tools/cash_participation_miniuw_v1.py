"""Internal explicit synthetic cash-share hypothesis, never personal approval."""
from pathlib import Path
import argparse,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from miniuw_foundation.cash_participation_artifacts import write_cash_participation_artifacts,audit_cash_participation_directory
from miniuw_foundation.drafts import ValidationError


def main():
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
    r=sub.add_parser('run');r.add_argument('case');r.add_argument('workbook');r.add_argument('--binding',required=True);r.add_argument('--terms',required=True);r.add_argument('--output',required=True)
    a=sub.add_parser('audit');a.add_argument('directory');args=parser.parse_args()
    try:
        result=(audit_cash_participation_directory(args.directory)if args.command=='audit'else write_cash_participation_artifacts(
            Path(args.case).read_bytes(),Path(args.workbook).read_bytes(),Path(args.binding).read_bytes(),Path(args.terms).read_bytes(),args.output))
    except(ValidationError,ValueError,OSError)as error:
        print(json.dumps(dict(status='blocked',reason=str(error),decision='PENDING',personal_investor_return_verified=False)),file=sys.stderr);return 2
    print(json.dumps(result));return 0


if __name__=='__main__':raise SystemExit(main())
