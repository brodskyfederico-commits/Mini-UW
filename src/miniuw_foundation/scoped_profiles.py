"""T09 explicit candidate DSCR profile over declared synthetic upstream amounts."""
from dataclasses import asdict, dataclass
from fractions import Fraction
import hashlib
import json
from pathlib import Path

from .drafts import ValidationError, canonical, digest, nonempty
from .calculations import (CalculationRun, CalculationGraph, CalculationNode, Operand,
    calculate_synthetic)

ENGINE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
PROFILE_ID = 'SYNTHETIC-DECLARED-DSCR-v1'
OUTPUT_NODE = '__scoped_dscr__'


def definition_sources():
    root=Path(__file__).resolve().parents[2]
    references=[('docs/model-refinance-contract.md',41,'DSCR=N/DS'),
        ('docs/refinance-capacity-bridge.md',13,'equivalente anualizado'),
        ('docs/refinance-capacity-bridge.md',29,'servicio cero'),
        ('sources/originals/95a304fd3e53__Reglas_de_la_casa_v5.1_Master_Prompt_Lorena.txt',84,'min DSCR')]
    result=[]
    for path,line,marker in references:
        try:
            raw=(root/path).read_bytes();lines=raw.decode('utf-8').splitlines()
        except (OSError,UnicodeError) as error:
            raise ValidationError('profile definition evidence unavailable') from error
        if len(lines)<line or marker not in lines[line-1]:
            raise ValidationError('profile source locator/definition changed')
        result.append({'path':path,'line':line,'sha256':hashlib.sha256(raw).hexdigest()})
    return result


@dataclass(frozen=True, kw_only=True)
class DscrBinding:
    profile_id: str
    definition_revision: str
    noi_node: str
    debt_service_node: str
    noi_producer_revision: str
    debt_service_producer_revision: str
    noi_basis_ref: str
    service_basis_ref: str
    service_basis: str
    expected_unit: str
    currency: str
    period_ref: str

    def __post_init__(self):
        for name,value in asdict(self).items():nonempty(value,name)
        if self.profile_id != PROFILE_ID:
            raise ValidationError('unsupported profile; explicit DSCR profile selection required')
        if self.service_basis not in ('declared_dated_period','regular_annual_sizing_equivalent'):
            raise ValidationError('explicit supported service basis required')
        if self.service_basis == 'regular_annual_sizing_equivalent' and self.expected_unit != 'currency/annual-sizing-equivalent':
            raise ValidationError('annual sizing profile requires an explicitly labelled equivalent unit')
        if self.noi_node == self.debt_service_node:
            raise ValidationError('NOI and service must be separately identified upstream quantities')


@dataclass(frozen=True)
class ScopedProfileRun:
    payload_json: str
    sha256: str

    @property
    def payload(self):
        return json.loads(self.payload_json)


def dispatch_scoped_profile(snapshot, profiles, normalization, graph, upstream, binding):
    if type(binding) is not DscrBinding:
        raise ValidationError('explicit supported profile binding required')
    if type(upstream) is not CalculationRun or calculate_synthetic(snapshot,profiles,normalization,graph) != upstream:
        raise ValidationError('upstream calculation must replay from exact snapshot/profiles/graph')
    prior=upstream.payload
    sources=definition_sources()
    records=prior['results']
    if binding.noi_node not in records or binding.debt_service_node not in records:
        raise ValidationError('profile references unavailable upstream nodes')
    if any(n.node_id == OUTPUT_NODE for n in graph.nodes):
        raise ValidationError('reserved profile output identity already used')
    blockers=[]
    expected={'kind':'money_per_period','unit':binding.expected_unit,
        'currency':binding.currency,'period':binding.period_ref}
    for role,key,revision in [('noi',binding.noi_node,binding.noi_producer_revision),
        ('debt_service',binding.debt_service_node,binding.debt_service_producer_revision)]:
        record=records[key]
        if record['definition']['definition_revision'] != revision:
            blockers.append(role+'_producer_revision_mismatch')
        if record['state'] != 'computed_synthetic':
            blockers.append(role+'_upstream_blocked')
        elif record['quantity'] != expected:
            blockers.append(role+'_quantity_unit_currency_or_period_mismatch')
    service=records[binding.debt_service_node]
    if service['state'] == 'computed_synthetic':
        ratio=service['rational']
        if Fraction(int(ratio['numerator']),int(ratio['denominator'])) <= 0:
            blockers.append('positive_debt_service_required_for_this_profile')
    if len(graph.nodes) >= 256:
        blockers.append('technical_graph_extension_bound')
    compiled=None;value=None
    if not blockers:
        scope=digest(canonical({'binding':asdict(binding),'sources':sources,'profile_engine_sha256':ENGINE_SHA256}))
        compiled_graph=CalculationGraph(graph_id='SYNTHETIC-profile-'+scope,
            definition_revision=binding.definition_revision,nodes=graph.nodes+(
                CalculationNode(node_id=OUTPUT_NODE,definition_revision=binding.definition_revision,
                    operation='ratio',operands=(Operand(kind='node',ref=binding.noi_node),
                        Operand(kind='node',ref=binding.debt_service_node))),))
        compiled=calculate_synthetic(snapshot,profiles,normalization,compiled_graph)
        output=compiled.payload['results'][OUTPUT_NODE]
        if output['state'] != 'computed_synthetic':
            blockers.extend(output['blockers'])
        else:value=output['rational']
    label=('synthetic_sizing_dscr_equivalent' if binding.service_basis == 'regular_annual_sizing_equivalent'
        else 'synthetic_dscr_for_declared_dated_period')
    payload={'component':'T09','purpose':'synthetic_development_only','profile_engine_sha256':ENGINE_SHA256,
        'binding':asdict(binding),'definition_sources':sources,'source':prior['source'],
        'normalization_sha256':normalization.sha256,'upstream_graph_sha256':graph.sha256,
        'upstream_run_sha256':upstream.sha256,'calculator_sha256':prior['engine_sha256'],
        'normalizer_sha256':prior['normalizer_sha256'],'state':'blocked' if blockers else 'computed_synthetic',
        'rational':value,'output_unit':'x','arithmetic_representation':'exact_rational','interpretation_label':label,
        'blockers':sorted(set(blockers)),'compiled_calculation':asdict(compiled) if compiled else None,
        'producer_role_claims_only':True,'upstream_contracts_financially_verified':False,
        'policy_adopted':False,'financially_validated':False,'decision':'PENDING',
        'run_ready':False,'production_authorized':False}
    encoded=canonical(payload)
    return ScopedProfileRun(encoded,digest(encoded))
