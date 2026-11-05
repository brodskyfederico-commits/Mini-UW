"""Local hypothetical participant cash observations; no new external decision PDF."""
from pathlib import Path
import argparse,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from miniuw_foundation.participant_cash_risk_artifacts import write_participant_cash_risk_artifacts,audit_participant_cash_risk_directory
from miniuw_foundation.drafts import ValidationError


def main():
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
    r=sub.add_parser('run');r.add_argument('allocation_evidence');r.add_argument('--output',required=True)
    a=sub.add_parser('audit');a.add_argument('directory');args=parser.parse_args()
    try:
        result=(audit_participant_cash_risk_directory(args.directory)if args.command=='audit'else
            write_participant_cash_risk_artifacts(Path(args.allocation_evidence).read_bytes(),args.output))
    except(ValidationError,ValueError,OSError)as error:
        print(json.dumps(dict(status='blocked',reason=str(error),decision='PENDING',verified_personal_investor_return=False)),file=sys.stderr);return 2
    print(json.dumps(result));return 0


if __name__=='__main__':raise SystemExit(main())
