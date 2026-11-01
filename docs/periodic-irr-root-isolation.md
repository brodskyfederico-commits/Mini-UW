# TIR periódica: conteo y aislamiento de raíces — referencia matemática

Se amplía el trabajo matemático independiente de M7 con `references/validate_periodic_irr_isolation.py`. No se activa un motor de underwriting, ni se elige una tasa entre alternativas. La referencia anterior `m7-validation.json` conserva su alcance histórico; esta ampliación tiene evidencia separada.

## Dominio y entradas expresas

Entradas: vector completo de flujos netos racionales en períodos igualmente espaciados, ancho máximo solicitado del intervalo de tasa periódica y presupuesto de bisecciones. Los tres son obligatorios; no hay precisión ni límite de trabajo predeterminados. Los parámetros sintéticos de la prueba no completan PAR-08 ni se convierten en configuración de un deal.

Con `q = 1 / (1 + r)`, el polinomio es `P(q) = CF0 + CF1*q + ... + CFn*q^n`. El dominio es `q > 0`, equivalente a `r > -1`. La periodicidad se declara para esta referencia: no se deduce de un calendario, no se comprimen períodos con cero y no se sustituyen datos faltantes por cero. Los flujos netos no reemplazan el ledger bruto de aportes/distribuciones usado por el equity multiple.

## Método exacto acotado

El cálculo usa división polinómica racional, máximo común divisor, parte libre de cuadrados y secuencias de Sturm. Cuenta raíces distintas en intervalos `(a,b]`, incluidos los casos sin cambio de signo de una raíz par. La multiplicidad se conserva por separado; una raíz doble no representa dos TIR distintas.

Una cota algebraica `B = 1 + max(abs(ai/an))` permite buscar todas las raíces positivas en `(0,B]`. Para `q >= B > 1`, la suma de los términos inferiores está acotada por `abs(an)*M*(q^n-1)/(q-1) < abs(an)*q^n`, con `M=max(abs(ai/an))`; no puede anular el término principal. Los factores `q=0`, cuando los flujos iniciales son cero, se excluyen expresamente: no son una tasa finita del dominio.

La bisección conserva el número exacto de raíces de cada subintervalo. Con una sola raíz, produce una raíz racional exacta si se encuentra un extremo que anula el polinomio; en otro caso entrega un intervalo racional de tasa cuyo ancho cumple el parámetro recibido. No pretende encontrar toda raíz racional en forma exacta ni produce decimales ficticiamente exactos para raíces irracionales.

El presupuesto limita las bisecciones de aislamiento, no todas las operaciones de álgebra ni el tamaño de sus coeficientes. Si se agota, se retienen los intervalos no resueltos y sus conteos, con estado incompleto. No se declara convergencia por haber encontrado la primera raíz.

## Salidas y tratamiento

| Caso matemático | Registro |
|---|---|
| Polinomio de flujos netos idénticamente cero | Indeterminado; no asignar TIR cero |
| Ninguna raíz positiva | Sin raíz admisible en este dominio; no equivale a FAIL económico |
| Una raíz distinta | Conservar intervalo o valor exacto y multiplicidad |
| Varias raíces distintas | Conservar todas; no elegir primera, mayor o más favorable |
| Límite de bisecciones alcanzado | Incompleto, con intervalos y conteos pendientes |

La transformación invierte los extremos: para `q` en `(a,b]`, la tasa está en `[1/b-1,1/a-1)` cuando `a>0`. Si todavía hay un extremo cero no se inventa una tasa finita. La tasa entregada es periódica; anualización, XIRR/fechas irregulares y reglas de selección requieren contratos separados.

## Evidencia y pendientes

Los controles cubren TIR positiva y negativa, dos tasas distintas, raíces dobles/triples, raíces irracionales y cercanas, polinomios sin raíces admisibles, ceros iniciales/finales, límites agotados y fronteras de subdivisión. La evidencia es una referencia aislada con casos sintéticos y oráculos por factores conocidos/encierros racionales. No es una auditoría independiente, validación bancaria, criterio de inversión, optimización global de precio o integración con el calendario/ledger del deal.

M7 mantiene abiertos la política de selección de raíces y demás requisitos de integración/revisión. Ninguna salida habilita PASS/FAIL: todos los resultados de esta referencia conservan PENDING y publicación desautorizada. Las métricas y criterios reales pendientes de Lorena continúan vacíos.
