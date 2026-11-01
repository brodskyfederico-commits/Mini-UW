"""One declared synthetic accounting bridge. Not a production engine or golden case."""
from fractions import Fraction as F
from pathlib import Path
import json
checks=[]
def check(name,condition):
 assert condition,name
 checks.append(name)
# Explicit abstract fixture assumptions, no real property, legal rates or Lorena criteria.
A=F(15);tax_floor=F(3);k=F(1,10);N=min(A-tax_floor,A/(1+k))
check('NOI_tax_residual',N==A-max(tax_floor,k*N)==12)
construction_cash_cost=F(30);opening_equity=F(10);construction_draw=F(20)
construction_period_rate=F(1,100);capitalized_interest=construction_draw*construction_period_rate
construction_payoff=construction_draw+capitalized_interest
check('construction_sources_cash_uses',opening_equity+construction_draw==construction_cash_cost)
check('construction_capitalization_no_extra_cash',construction_payoff==F(101,5))
check('explicit_synthetic_debt_limit',construction_payoff<=F(21))
# Different explicit permanent-loan terms: zero period rate, six monthly arrears payments.
periods_per_year=12;amortization_payments=6;unit_payment=F(1,amortization_payments)
constant=periods_per_year*unit_payment;value=N/F(1,10)
ltv_capacity=F(1,2)*value;dscr_capacity=N/(F(2)*constant)
loan=min(ltv_capacity,dscr_capacity);payment=loan*unit_payment
check('DSCR_binding',loan==dscr_capacity==3 and loan<ltv_capacity)
fee=F(1,10)*loan;restricted_reserve=F(1)
refi_equity=construction_payoff+fee+restricted_reserve-loan
check('refi_cash_in_and_restricted_reserve',loan+refi_equity==construction_payoff+fee+restricted_reserve and refi_equity==F(37,2))
# Holding cash NOI assumed fully collected/paid in three explicit months, no growth.
monthly_noi=N/12;balance=loan;operations_distributions=[]
for month in [3,4,5]:
 balance-=payment;operations_distributions.append(monthly_noi-payment)
 check('holding_month_'+str(month),monthly_noi==payment+operations_distributions[-1] and balance>=0)
check('maturity_vs_amortization_balloon',balance==F(3,2)>0)
# Close at end of third holding month; forward NOI is valuation only, not another receipt.
forward_noi=N;gross_sale=forward_noi/F(1,10);selling_cost=F(1,10)*gross_sale
terminal_distribution=gross_sale+restricted_reserve-selling_cost-balance
check('terminal_cash_no_double_count',gross_sale+restricted_reserve==selling_cost+balance+terminal_distribution)
gross_contributions=[opening_equity,refi_equity]
gross_distributions=operations_distributions+[terminal_distribution]
EM=sum(gross_distributions)/sum(gross_contributions)
check('gross_equity_multiple',EM==F(218,57))
check('whole_life_cash_sources_uses',opening_equity+construction_draw+loan+refi_equity+3*monthly_noi+gross_sale==construction_cash_cost+construction_payoff+fee+3*payment+selling_cost+balance+sum(gross_distributions))
# Restricted reserve is an internal transfer/release, not an additional whole-life source.
net_by_period=[-opening_equity,F(0),-refi_equity,*operations_distributions]
net_by_period[-1]+=terminal_distribution
check('investor_net_vs_gross',sum(net_by_period)==sum(gross_distributions)-sum(gross_contributions))
result={
 'status':'passed','fixture':'SYNTHETIC-BRIDGE-01','arithmetic':'exact rational','checks':checks,'total':len(checks),
 'assumptions':['Abstract synthetic amounts; no project/market/legal inputs','Declared affine tax proxy/floor only, not verified tax policy','Construction costs funded by explicit equity/draw; opening debt carries one period interest capitalized; explicit limit 21','Refi uses explicit zero-rate permanent loan, six monthly amortizing payments, monthly cash NOI and 3-month hold','Fees/reserve/sale cost explicit synthetic fractions; reserves released once at sale','No cash accrual differences, growth or extra restrictions; sale at end of last operating period','Three-month maturity has remaining principal; payoff at exit, no fictional extension'],
 'results':{'NOI_annual':str(N),'construction_payoff':str(construction_payoff),'permanent_loan':str(loan),'refi_equity_cash_in':str(refi_equity),'balloon_at_exit':str(balance),'gross_sale':str(gross_sale),'terminal_distribution':str(terminal_distribution),'gross_contributions':str(sum(gross_contributions)),'gross_distributions':str(sum(gross_distributions)),'equity_multiple':str(EM)},
 'IRR':'not calculated; no general root solver certified','decision':'not evaluated; no Lorena criteria or house policy entered',
 'scope':'One scoped M2-to-M7 cash/debt/equity bridge under declared synthetic assumptions. Not independent validation, original acceptance golden case, full circular-financing solver, production integration or product release.'}
Path(__file__).with_name('integrated-bridge-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
