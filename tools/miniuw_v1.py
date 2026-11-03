"""Run or audit Mini-UW v1 synthetic local artifacts. No network or deployment."""
from pathlib import Path
import argparse
import json
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.v1_artifacts import write_case_artifacts,audit_directory


def main(argv=None):
    parser=argparse.ArgumentParser(description='Mini-UW v1: integracion sintetica local, decision PENDIENTE')
    sub=parser.add_subparsers(dest='command',required=True)
    run=sub.add_parser('run');run.add_argument('case');run.add_argument('--output',required=True)
    audit=sub.add_parser('audit');audit.add_argument('directory')
    args=parser.parse_args(argv)
    try:
        result=write_case_artifacts(Path(args.case).read_bytes(),args.output)if args.command=='run'else audit_directory(args.directory)
    except (ValidationError,OSError,ValueError)as error:
        print(json.dumps(dict(status='blocked',reason=str(error),decision='PENDING',real_decisions_enabled=False),ensure_ascii=False),file=sys.stderr)
        return 2
    print(json.dumps(result,ensure_ascii=False));return 0


if __name__=='__main__':raise SystemExit(main())
