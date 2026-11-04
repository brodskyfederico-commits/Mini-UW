"""Local synthetic original-layout worksheet/case run and audit."""
from pathlib import Path
import argparse,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from miniuw_foundation.worksheet_case_artifacts import write_worksheet_case_artifacts,audit_worksheet_case_directory
from miniuw_foundation.drafts import ValidationError


def main():
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
    r=sub.add_parser('run');r.add_argument('case');r.add_argument('workbook');r.add_argument('--binding',required=True);r.add_argument('--output',required=True)
    a=sub.add_parser('audit');a.add_argument('directory');args=parser.parse_args()
    try:
        result=(audit_worksheet_case_directory(args.directory)if args.command=='audit'else
            write_worksheet_case_artifacts(Path(args.case).read_bytes(),Path(args.workbook).read_bytes(),Path(args.binding).read_bytes(),args.output))
    except(ValidationError,ValueError,OSError)as error:
        print(json.dumps(dict(status='blocked',reason=str(error),decision='PENDING',worksheet_values_adopted=False)),file=sys.stderr);return 2
    print(json.dumps(result));return 0


if __name__=='__main__':raise SystemExit(main())
