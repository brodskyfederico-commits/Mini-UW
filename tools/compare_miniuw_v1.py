"""Local synthetic full-revision comparison. No candidate generation or network."""
from pathlib import Path
import argparse
import json
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from miniuw_foundation.drafts import ValidationError
from miniuw_foundation.v1_revision_bundle import write_comparison_artifacts,audit_comparison_directory


def main(argv=None):
    parser=argparse.ArgumentParser(description='Comparar revisiones completas sinteticas del Mini-UW v1')
    sub=parser.add_subparsers(dest='command',required=True)
    run=sub.add_parser('compare');run.add_argument('--reference',required=True);run.add_argument('--candidate',required=True);run.add_argument('--spec',required=True);run.add_argument('--output',required=True)
    audit=sub.add_parser('audit');audit.add_argument('directory')
    args=parser.parse_args(argv)
    try:
        result=audit_comparison_directory(args.directory)if args.command=='audit'else write_comparison_artifacts(Path(args.reference).read_bytes(),Path(args.candidate).read_bytes(),Path(args.spec).read_bytes(),args.output)
    except (ValidationError,OSError,ValueError)as error:
        print(json.dumps(dict(status='blocked',reason=str(error),decision='PENDING',real_decisions_enabled=False),ensure_ascii=False),file=sys.stderr);return 2
    print(json.dumps(result,ensure_ascii=False));return 0


if __name__=='__main__':raise SystemExit(main())
