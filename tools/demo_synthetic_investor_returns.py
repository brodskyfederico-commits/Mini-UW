"""Reopen a temporary archive and report a declared synthetic $10 cash story."""
from pathlib import Path
from fractions import Fraction
import json,tempfile
from miniuw_foundation.investor_returns import produce_investor_returns
from miniuw_foundation.archive import EvidenceArchive


def main():
    root=Path(__file__).resolve().parents[1];raw=(root/'templates/synthetic-investor-returns.json').read_bytes()
    run=produce_investor_returns(raw)
    with tempfile.TemporaryDirectory()as temporary:
        path=Path(temporary)/'cash.sqlite3'
        with EvidenceArchive(path)as a:bundle=a.save_investor_returns(raw,run)
        with EvidenceArchive(path)as a:
            recovered=a.load_investor_returns(bundle)
            assert recovered.run==run and a.get_investor_returns_source(recovered.payload['source_sha256'])==raw
    p=run.payload;n=p['normalized_story']
    def exact(q):return str(Fraction(int(q['numerator']),int(q['denominator'])))
    lines=['EJEMPLO SINTETICO: equity agregado del proyecto, no retorno contractual de un LP.',
        'Normalizacion sobre los aportes expresamente elegidos: '+', '.join(n['basis_event_ids'])+'.']
    for e in n['events']:lines.append(e['date']+' | '+e['kind']+' | '+e['category']+' | USD '+exact(e['amount']))
    lines.append('Aportes totales: USD '+exact(n['total_contributions'])+'; cobros totales: USD '+exact(n['total_distributions'])+'; ganancia de caja: USD '+exact(n['net_cash_profit'])+'; EM: '+exact(n['equity_multiple'])+'x.')
    for s in p['capital_snapshots']:
        lines.append(s['as_of_date']+' | Capital aun invertido declarado: USD '+exact(s['normalized_capital_still_invested'])+'; valor retenido declarado: USD '+exact(s['normalized_retained_equity_value'])+' (no sumado a los cobros).')
    for row in p['annual_cash_receipts']:
        lines.append(str(row['calendar_cash_receipt_year'])+' | Distribucion operativa normalizada: USD '+exact(row['normalized_operating_distributions'])+'; CoC condicionado: '+exact(row['conditional_coc'])+'.')
    def percent_bound(q,upper):
        value=Fraction(int(q['numerator']),int(q['denominator']))*100*10**6
        integer=-((-value.numerator)//value.denominator) if upper else value.numerator//value.denominator
        sign='-'if integer<0 else'';whole,part=divmod(abs(integer),10**6)
        return sign+str(whole)+'.'+str(part).zfill(6)+'%'
    for index,root in enumerate(p['annual_irr_roots']):
        interval=root['annual_rate_interval']
        if interval is not None:
            lines.append('TIR anual, solucion '+str(index+1)+': contenida entre '+percent_bound(interval['lower'],False)+' y '+percent_bound(interval['upper'],True)+' (limites de presentacion ampliados hacia afuera).')
        else:lines.append('TIR anual exacta: '+exact(root['exact_annual_rate'])+' como fraccion anual.')
    lines.append('Se conservan los intervalos certificados exactos en annual_irr_roots; no se selecciona una tasa para decidir.')
    lines.append('Proyecciones suministradas, no producidas desde costos/NOI/banco. Pendientes: conciliacion financiera, riesgos, impuestos y waterfall/LP si corresponde; PDF final y decisiones reales no habilitados.')
    return {'purpose':'declared_synthetic_investor_cash_return_demonstration','human_readable_story':lines,
        'source_sha256':p['source_sha256'],'run_sha256':run.sha256,'bundle_sha256':bundle,
        'replayed_after_reopen':True,'source_bytes_preserved':True,'runtime_database_retained':False,'result':p}


if __name__=='__main__':print(json.dumps(main(),ensure_ascii=False,indent=2))
