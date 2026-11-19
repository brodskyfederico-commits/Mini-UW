"""Versioned exact cash transport with isolated, source-pinned dependencies.

Reuse the reviewed function code with a larger bounded rational reader. Each
function gets its own execution namespace; imported modules and their globals
are never patched. Arithmetic budgets and financial formula code stay intact.
"""
import hashlib
from importlib import import_module
import json
from pathlib import Path
from types import FunctionType, ModuleType

from check_operating_replay_D20 import require
from miniuw_foundation.debt_service import _fraction as legacy_fraction


PROFILE = "miniuw.synthetic-exact-cash-transport.v1"
MAX_INTEGER_DIGITS = 1300
ROOT = Path(__file__).resolve().parents[1]
ALGORITHMS = {
    "miniuw_foundation.operating_cash": "1c23d1c6d629e98eb2448f2ab697bf2970dda501275c072ac64109d4f36ef6f1",
    "miniuw_foundation.closing_cash": "7053bbdba91ad38d55909308fc6aef809449944ebae02c1ec387b1bfd810487b",
    "miniuw_foundation.investor_returns": "b64f5bae914ce97edebc4a86849935952eea4a25e271068d92b0f2197843b036",
    "miniuw_foundation.closing_returns": "59c090460087d46f82fd9930c004a12dcc4368dc521fae7959c802587fc1df64",
    "miniuw_foundation.debt_closing": "1cba940c460b048132c57668ff893e2f4bdc68ab93f286be20a0f81b163f1947",
    "miniuw_foundation.refinance_capacity": "b3250d05ecf4af5c15596d271770bb5f2ec99b73acb022efe96ea5e40be977bf",
    "plan_return_D107": "acda5f1b863c9538619b6dbebbbf95b20f099f36523da1239c27fc6347c74f8d",
    "plan_refinance_D108": "3a789dbd81a52221ac16b7617e5c9e3967dbfb65101fae5735475e6c420afd7d",
}
DEPENDENCIES = {
    "miniuw_foundation.debt_service": "04d34f9479ebc802bc255d3a47c267469bdaadfee61871d174b2d0eee43d170f",
    "miniuw_foundation.operating_noi": "034fda6791ce3386d2345fa7015d9a9ca6f2003e0e71664216d3939d268eaafd",
    "miniuw_foundation.periodic_returns": "eac518ac1fe44b196ba047965a28aef1e60067c48f8b7876963bab857257e4e2",
}


def exact_fraction(record, max_digits=MAX_INTEGER_DIGITS):
    return legacy_fraction(record, min(max_digits, MAX_INTEGER_DIGITS))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def cash_engine():
    from miniuw_foundation import debt_service, operating_noi

    require(debt_service.MAX_BITS == operating_noi.MAX_BITS == 4096,
            "exact_cash_arithmetic_budget_revision_unconfirmed")
    originals = {name: import_module(name) for name in ALGORITHMS}
    rows = []
    for name, expected in (ALGORITHMS | DEPENDENCIES).items():
        module = originals[name] if name in originals else import_module(name)
        path = Path(module.__file__).resolve()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        require(digest == expected, f"exact_cash_algorithm_revision_unconfirmed:{name}")
        rows.append(dict(module=name, path=str(path.relative_to(ROOT)), algorithm_sha256=digest,
                         isolated_transport=name in ALGORITHMS))
    descriptor = dict(profile=PROFILE, adapter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        max_integer_digits=MAX_INTEGER_DIGITS, arithmetic_max_bits=4096, rounding="none",
        global_mutation=False, algorithms=rows,
        numeric_reader_sha256=hashlib.sha256(Path(debt_service.__file__).read_bytes()).hexdigest())
    descriptor["revision_sha256"] = hashlib.sha256(canonical(descriptor)).hexdigest()

    namespaces = {name: ModuleType(f"{PROFILE}:{name}") for name in originals}
    functions = {}
    for name, module in originals.items():
        env = namespaces[name].__dict__
        env.update(vars(module))
        for key, value in vars(module).items():
            if isinstance(value, FunctionType) and value.__module__ == name:
                fn = FunctionType(value.__code__, env, value.__name__, value.__defaults__, value.__closure__)
                fn.__kwdefaults__ = None if value.__kwdefaults__ is None else dict(value.__kwdefaults__)
                fn.__annotations__ = dict(value.__annotations__)
                fn.__qualname__ = value.__qualname__
                functions[value] = fn
                env[key] = fn

    by_module = {id(originals[name]): namespaces[name] for name in originals}
    for name, namespace in namespaces.items():
        env = namespace.__dict__
        for key, value in tuple(env.items()):
            if isinstance(value, FunctionType) and value in functions:
                env[key] = functions[value]
            elif isinstance(value, ModuleType) and id(value) in by_module:
                env[key] = by_module[id(value)]
        env["_fraction"] = exact_fraction
        env["ENGINE_SHA256"] = hashlib.sha256(canonical(dict(
            algorithm_sha256=ALGORITHMS[name], transport_revision_sha256=descriptor["revision_sha256"]))).hexdigest()
    return namespaces["plan_refinance_D108"].financed_cash, descriptor
