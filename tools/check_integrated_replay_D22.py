"""Replay construction debt, operating cash and sale for both archived synthetic versions."""
import json
import sys

from check_debt_sale_replay_D21 import run as replay_debt_and_sale
from check_operating_replay_D20 import ROOT, replay_snapshots, require


def run(root=ROOT):
    operations = replay_snapshots(root)
    by_input = {result["input_ref"]["path"]: result for result in operations}
    require(len(by_input) == len(operations), "Duplicate operating input")
    replay = replay_debt_and_sale(root, operating_by_input=by_input)
    return dict(scope="archived_synthetic", currency="USD", **replay)


if __name__ == "__main__":
    try:
        print(json.dumps(run(), ensure_ascii=False))
    except (ValueError, TypeError, OSError, KeyError, IndexError) as error:
        print(json.dumps({"status": "failed", "reason": str(error)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
