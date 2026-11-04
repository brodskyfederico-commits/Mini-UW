"""Run/audit local synthetic Mini-UW successive insurance policy profiles."""
from pathlib import Path
import argparse,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.policy_renewal_artifacts import write_policy_renewal_artifacts,audit_policy_renewal_directory


def main(argv=None):
    parser=argparse.ArgumentParser(description='Mini-UW sintetico con renovaciones de seguros suministradas')
    sub=parser.add_subparsers(dest='command',required=True);run=sub.add_parser('run');run.add_argument('case');run.add_argument('--output',required=True);audit=sub.add_parser('audit');audit.add_argument('directory');args=parser.parse_args(argv)
    try:result=write_policy_renewal_artifacts(Path(args.case).read_bytes(),args.output)if args.command=='run'else audit_policy_renewal_directory(args.directory)
    except (ValidationError,ValueError,OSError)as error:
        print(json.dumps(dict(status='blocked',reason=str(error),decision='PENDING',real_decisions_enabled=False),ensure_ascii=False),file=sys.stderr);return 2
    print(json.dumps(result,ensure_ascii=False));return 0


if __name__=='__main__':raise SystemExit(main())
