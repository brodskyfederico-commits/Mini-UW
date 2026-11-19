"""Explicit exact transport for the integrated synthetic input and screening path."""
import hashlib
from pathlib import Path
from types import FunctionType

from check_operating_replay_D20 import require
from miniuw_foundation import screening
from worksheet_exact_cash_D263 import canonical, cash_engine, exact_fraction
from worksheet_local_sources_D127 import synthetic_id


PROFILE = "miniuw.synthetic-integrated-exact-transport.v1"
SCREENING_SHA256 = "52701de576e82c52d0d156ecc8b5801132250427ef5b02dc2393bbdcc6538137"


def integrated_engines(config, *, technical):
    require(technical and isinstance(config, dict) and config.keys() == {"profile", "source_ref"}
            and config["profile"] == PROFILE and synthetic_id(config["source_ref"]),
            "integrated_exact_transport_configuration_unconfirmed")
    digest = hashlib.sha256(Path(screening.__file__).read_bytes()).hexdigest()
    require(digest == SCREENING_SHA256, "integrated_exact_screening_revision_unconfirmed")
    engine, cash_descriptor = cash_engine()
    descriptor = dict(profile=PROFILE, source_ref=config["source_ref"], cash_transport=cash_descriptor,
        screening_algorithm_sha256=digest, max_integer_digits=1300, rounding="none",
        adapter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    descriptor["revision_sha256"] = hashlib.sha256(canonical(descriptor)).hexdigest()
    env = dict(vars(screening))
    for key, fn in vars(screening).items():
        if isinstance(fn, FunctionType) and fn.__module__ == screening.__name__:
            copy = FunctionType(fn.__code__, env, fn.__name__, fn.__defaults__, fn.__closure__)
            copy.__kwdefaults__ = None if fn.__kwdefaults__ is None else dict(fn.__kwdefaults__)
            env[key] = copy
    env["_fraction"] = exact_fraction
    env["ENGINE_SHA256"] = hashlib.sha256(canonical(dict(
        algorithm_sha256=digest, transport_revision_sha256=descriptor["revision_sha256"]))).hexdigest()
    return engine, env["simulate_screening"], descriptor
