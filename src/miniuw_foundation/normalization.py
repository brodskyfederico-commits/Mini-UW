"""T07 exact numeric decoding under explicit synthetic profiles, never financial adoption."""
from dataclasses import asdict, dataclass
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re

from .drafts import ValidationError, canonical, digest, nonempty
from .execution import _snapshot_payload

ENGINE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


@dataclass(frozen=True, kw_only=True)
class NumericProfile:
    profile_id: str
    definition_revision: str
    slot_id: str
    source_definition_ref: str | None
    decimal_mark: str
    notation: str
    trim_outer_whitespace: bool
    source_unit_literal: str
    target_unit: str
    quantity_kind: str
    currency_literal: str | None
    period_literal: str | None

    def __post_init__(self):
        for name in ('profile_id','definition_revision','slot_id','source_unit_literal','target_unit'):
            nonempty(getattr(self,name),name)
        if not self.profile_id.startswith('SYNTHETIC-'):
            raise ValidationError('explicit synthetic numeric profile required')
        for name in ('source_definition_ref','currency_literal','period_literal'):
            if getattr(self,name) is not None:
                nonempty(getattr(self,name),name)
        if self.decimal_mark not in ('.',',') or self.notation not in ('decimal','percent_suffix'):
            raise ValidationError('explicit decimal mark and supported notation required')
        if type(self.trim_outer_whitespace) is not bool:
            raise ValidationError('explicit whitespace policy required')
        if self.quantity_kind not in ('scalar','money','money_per_period'):
            raise ValidationError('unsupported synthetic quantity kind')
        if self.quantity_kind == 'scalar' and (self.currency_literal is not None or self.period_literal is not None):
            raise ValidationError('scalar fixture cannot carry money/period semantics')
        if self.quantity_kind in ('money','money_per_period') and self.currency_literal is None:
            raise ValidationError('money requires an explicit currency, never inferred from a symbol')
        if self.quantity_kind == 'money_per_period' and self.period_literal is None:
            raise ValidationError('periodic money requires an explicit period identity')
        if self.notation == 'percent_suffix':
            if (self.quantity_kind != 'scalar' or self.source_unit_literal != '%'
                or self.target_unit != 'fraction'):
                raise ValidationError('only explicit percent-to-fraction scaling is implemented')
        elif self.source_unit_literal != self.target_unit:
            raise ValidationError('decimal identity only; no implicit unit, time or currency conversion')


@dataclass(frozen=True)
class NormalizationRun:
    payload_json: str
    sha256: str

    @property
    def payload(self):
        return json.loads(self.payload_json)


def _profiles(snapshot, profiles):
    if type(profiles) is not tuple or not profiles or any(type(p) is not NumericProfile for p in profiles):
        raise ValidationError('explicit nonempty immutable numeric profile tuple required')
    if len({p.slot_id for p in profiles}) != len(profiles) or len({p.profile_id for p in profiles}) != len(profiles):
        raise ValidationError('duplicate slot/profile identity; no last-wins selection')
    for profile in profiles:
        snapshot.slot('input',profile.slot_id)  # Criteria cannot be adopted via this adapter.
    return tuple(sorted(profiles,key=lambda p:p.slot_id))


def _number(literal, profile):
    if len(literal) > 256:
        return None, 'numeric_text_too_long'
    text = literal.strip() if profile.trim_outer_whitespace else literal
    if profile.notation == 'percent_suffix':
        if not text.endswith('%'):
            return None, 'explicit_percent_suffix_missing'
        text = text[:-1]
    mark = re.escape(profile.decimal_mark)
    if not re.fullmatch(r'[-+]?[0-9]+(?:'+mark+r'[0-9]+)?',text):
        return None, 'unsupported_or_ambiguous_numeric_text'
    value = Fraction(text.replace(',','.'))
    if profile.notation == 'percent_suffix':
        value /= 100  # Mathematical representation, not an investment threshold.
    return value, None


def normalize_synthetic(snapshot, profiles):
    source = _snapshot_payload(snapshot)
    ordered = _profiles(snapshot,profiles)
    results = {}
    for profile in ordered:
        slot = snapshot.slot('input',profile.slot_id)
        claims = slot['claims']
        blockers = []
        if slot['state'] == 'missing':
            blockers.append('missing_literal')
        elif slot['state'] == 'conflicting_claims':
            blockers.append('unresolved_source_conflict')
        if claims and slot['has_blank_claims'] and slot['state'] != 'missing':
            blockers.append('blank_and_present_claims_require_resolution')
        for record in claims:
            for key, expected in [('unit_literal',profile.source_unit_literal),
                ('currency_literal',profile.currency_literal),
                ('period_literal',profile.period_literal),
                ('definition_ref',profile.source_definition_ref)]:
                if record[key] != expected:
                    blockers.append('source_'+key+'_mismatch_or_missing')
        number = None
        if not blockers:
            # All claims must have identical nonblank literals and explicit metadata.
            number, failure = _number(claims[0]['literal'],profile)
            if failure:
                blockers.append(failure)
        results[profile.slot_id] = {'state':'blocked' if blockers else 'decoded_synthetic',
            'rational':None if number is None else {'numerator':str(number.numerator),'denominator':str(number.denominator)},
            'target_unit':profile.target_unit,'currency_literal':profile.currency_literal,
            'period_literal':profile.period_literal,'profile':asdict(profile),
            'source_claims':claims,'blockers':sorted(set(blockers)),
            'financially_validated':False}
    payload = {'component':'T07','purpose':'synthetic_development_only',
        'engine_sha256':ENGINE_SHA256,
        'source':{'draft_id':snapshot.draft_id,'revision':snapshot.revision,
            'sha256':snapshot.sha256,'context':source['context']},
        'profiles_sha256':digest(canonical([asdict(p) for p in ordered])),
        'results':results,'decision':'PENDING','run_ready':False,
        'financially_normalized':False,'production_authorized':False}
    encoded = canonical(payload)
    return NormalizationRun(encoded,digest(encoded))


def observe_normalization_freshness(run, snapshot, profiles):
    if type(run) is not NormalizationRun or digest(run.payload_json) != run.sha256:
        raise ValidationError('intact normalization run required')
    prior = run.payload
    if prior.get('component') != 'T07' or prior.get('decision') != 'PENDING' or prior.get('production_authorized') is not False or prior.get('run_ready') is not False:
        raise ValidationError('synthetic normalization guards changed')
    current = normalize_synthetic(snapshot,profiles).payload
    source_current = prior['source'] == current['source']
    profile_current = prior['profiles_sha256'] == current['profiles_sha256']
    engine_current = prior['engine_sha256'] == ENGINE_SHA256
    return {'source_snapshot_current':source_current,'profiles_current':profile_current,
        'engine_current':engine_current,
        'entire_run_current':source_current and profile_current and engine_current,
        'observation_only':True,'publication_authorized':False,'decision':'PENDING'}
