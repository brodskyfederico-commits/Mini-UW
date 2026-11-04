"""Create/audit a synthetic revision review; never adopt its candidate."""
from pathlib import Path
import argparse,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from miniuw_foundation.irr_review_artifacts import write_review_artifacts,audit_review_directory
from miniuw_foundation.drafts import ValidationError


def main():
    parser=argparse.ArgumentParser(description='Mini-UW: revision candidata reproducida, sin adopcion')
    sub=parser.add_subparsers(dest='command',required=True)
    c=sub.add_parser('compare');c.add_argument('reference');c.add_argument('candidate');c.add_argument('--spec',required=True);c.add_argument('--output',required=True)
    a=sub.add_parser('audit');a.add_argument('directory');args=parser.parse_args()
    try:
        result=(write_review_artifacts(Path(args.reference).read_bytes(),Path(args.candidate).read_bytes(),Path(args.spec).read_bytes(),args.output)
            if args.command=='compare'else audit_review_directory(args.directory))
    except(ValidationError,ValueError,OSError)as error:
        print(json.dumps(dict(status='blocked',reason=str(error),candidate_adopted=False,decision='PENDING'),ensure_ascii=False),file=sys.stderr);return 2
    print(json.dumps(result,ensure_ascii=False));return 0


if __name__=='__main__':raise SystemExit(main())
