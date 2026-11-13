"""Exercise the proposed reserve-adjusted performance and fixed-debt price bases."""
from fractions import Fraction


BEFORE_RESERVES = "before_replacement_reserves"
AFTER_RESERVES = "after_replacement_reserves"
MINIMUM_METRICS = ("yield_or_spread", "annual_irr", "equity_multiple")
METRICS = (*MINIMUM_METRICS, "equity_to_tdc")


def performance(noi, reserve, cost, cap, cap_basis, post_refi_noi, post_refi_reserve, service, equity):
    yoc_before = noi / cost
    yoc = (noi - reserve) / cost
    spread_yield = {BEFORE_RESERVES: yoc_before, AFTER_RESERVES: yoc}.get(cap_basis)
    spread = None if cap is None or spread_yield is None else (spread_yield - cap) * 10_000
    return dict(noi_uw=noi - reserve, yoc=yoc, spread_yoc=spread_yield, cap_noi_basis=cap_basis,
                spread_bps=spread, spread_state="PENDING" if spread is None else "calculated_synthetic",
                spread_blocker="cap_noi_basis_or_value_missing" if spread is None else None,
                coc=(post_refi_noi - post_refi_reserve - service) / equity, coc_annualized=False)


def equilibrium(slope, intercept, floor, tax_coefficient, debt_service, reserve, *, credit_loss=None, concessions=None):
    # In this trial, the tax floor and coefficient refer to the pre-reserve NOI.
    pre_reserve_target = debt_service + reserve
    tax = max(floor, tax_coefficient * pre_reserve_target)
    crossing = (pre_reserve_target + tax - intercept) / slope
    economic = max(Fraction(), crossing)
    result = dict(economic=economic, algebraic_crossing=crossing, tax_at_crossing=tax,
                  economic_state="not_attainable" if economic > 1 else "calculated_synthetic",
                  physical=None, physical_state="PENDING", physical_blocker="C14_sin_desglose")
    if credit_loss is None or concessions is None:
        return result
    if not (0 <= credit_loss < 1 and 0 <= concessions < 1):
        return result | dict(physical_blocker="factor_de_cobro_no_positivo_o_invalido")
    physical = economic / ((1 - credit_loss) * (1 - concessions))
    return result | dict(physical=physical, physical_state="not_attainable" if physical > 1 else "calculated_synthetic",
                         physical_blocker=None)


def price_screen(source, rules, grid):
    """Find joint price limits on a declared grid with exact signed cash and rates."""
    low, high, step = grid
    if any(type(value) is not int for value in grid) or step <= 0 or not 2 * step <= high - low <= 1000 * step:
        raise ValueError("explicit bounded price grid required")
    points = range(low, high + 1, step)
    if points[-1] != high or rules.keys() != set(METRICS):
        raise ValueError("explicit bounded price grid and complete synthetic criteria required")
    for metric, (pass_op, pass_value, fail_op, fail_value) in rules.items():
        minimum = metric in MINIMUM_METRICS
        if (pass_op, fail_op) != ((">=", "<") if minimum else ("<=", ">")) or (
                pass_value < fail_value if minimum else pass_value > fail_value):
            return dict(state="PENDING", blocker="criterion_direction_or_band_unconfirmed", pass_price=None, before_fail=None)
    flows = source["net_flows"]
    cap = source["cap"] if source["cap"] is not None else Fraction()
    cap_basis = source["cap_noi_basis"]
    if source["cap"] is not None and cap_basis not in (BEFORE_RESERVES, AFTER_RESERVES):
        return dict(state="PENDING", blocker="cap_noi_basis_missing", pass_price=None, before_fail=None)
    yield_noi = source["noi_before"] if cap_basis == BEFORE_RESERVES and source["cap"] is not None else source["noi_uw"]
    if yield_noi <= 0 or source["debt"] < 0 or source["closing_rate"] < 0 or source["distributions"] <= 0:
        raise ValueError("unsupported cost, debt, revenue or reserve profile")

    # An annual TIR hurdle uses an explicit exact quarterly equivalent in this trial.
    # With one negative-to-positive sign change, its NPV sign orders the unique TIR.
    irr = rules["annual_irr"]
    hurdles = source["quarterly_irr_thresholds"]
    if any(rate <= -1 or (1 + rate) ** 4 - 1 != threshold
           for rate, threshold in zip(hurdles, (irr[1], irr[3]), strict=True)):
        return dict(state="PENDING", blocker="annual_and_quarterly_irr_threshold_mismatch", pass_price=None, before_fail=None)
    future_pv = [sum((flow / (1 + rate) ** index for index, flow in enumerate(flows) if index), Fraction())
                 for rate in hurdles]
    nonzero = [x for x in flows[1:] if x]
    if not nonzero or nonzero[-1] <= 0 or any(a > 0 > b for a, b in zip(nonzero, nonzero[1:])):
        return dict(state="PENDING", blocker="irr_monotonicity_unproven", pass_price=None, before_fail=None)

    def evaluate(price):
        change = (price - source["price"]) * (1 + source["closing_rate"])
        tdc, equity = source["tdc"] + change, source["applied_equity"] + change
        contributions, first = source["contributions"] + change, flows[0] - change
        if tdc <= 0 or equity < 0 or equity + source["debt"] != tdc or contributions <= 0 or first >= 0:
            return None
        values = dict(yield_or_spread=(yield_noi / tdc - cap) * (10_000 if source["cap"] is not None else 1),
                      equity_multiple=source["distributions"] / contributions, equity_to_tdc=equity / tdc)
        comparisons = {}
        for metric, (_, pass_value, _, fail_value) in rules.items():
            if metric == "annual_irr":
                passing, failing = first + future_pv[0] >= 0, first + future_pv[1] < 0
            elif metric in MINIMUM_METRICS:
                passing, failing = values[metric] >= pass_value, values[metric] < fail_value
            else:
                passing, failing = values[metric] <= pass_value, values[metric] > fail_value
            comparisons[metric] = "PASS" if passing else "FAIL" if failing else "PENDING"
        overall = "FAIL" if "FAIL" in comparisons.values() else "PENDING" if "PENDING" in comparisons.values() else "PASS"
        return dict(price=price, delta_tdc=change, debt=source["debt"], values=values, comparisons=comparisons,
                    state=overall)

    rows = [evaluate(price) for price in points]
    if any(row is None for row in rows):
        return dict(state="PENDING", blocker="price_grid_outside_positive_equity_or_cost_domain", pass_price=None, before_fail=None)
    severity = {"PASS": 0, "PENDING": 1, "FAIL": 2}
    if any(severity[a["comparisons"][m]] > severity[b["comparisons"][m]]
           for a, b in zip(rows, rows[1:]) for m in METRICS):
        return dict(state="PENDING", blocker="criterion_status_not_monotone_on_grid", pass_price=None, before_fail=None)

    def limit(allowed):
        eligible = [i for i, row in enumerate(rows) if row["state"] in allowed]
        if not eligible:
            return dict(state="not_attainable_on_grid", price=None, below=None, at=None, above=None)
        index = eligible[-1]
        at = rows[index]
        below = rows[index - 1] if index else None
        above = rows[index + 1] if index + 1 < len(rows) else None
        state = "upper_bound_unresolved" if above is None else "bounded_synthetic"
        return dict(state=state, price=at["price"] if above is not None else None, below=below, at=at, above=above)

    passing = limit({"PASS"})
    before_fail = limit({"PASS", "PENDING"})
    return dict(state="PENDING" if any(r["price"] is None for r in (passing, before_fail)) else "calculated_synthetic",
                blocker=next((r["state"] for r in (passing, before_fail) if r["price"] is None), None),
                pass_price=passing["price"], before_fail=before_fail["price"],
                yield_criterion="spread_bps" if source["cap"] is not None else "yoc_uw",
                negative_pass_price=passing["price"] is not None and passing["price"] < 0,
                evaluated_prices=len(rows), grid=list(grid), monotone_on_grid=True,
                pass_boundary=passing, before_fail_boundary=before_fail,
                asking_over_pass_price=(source["asking"] / passing["price"]
                                        if passing["price"] is not None and passing["price"] > 0 else None))
