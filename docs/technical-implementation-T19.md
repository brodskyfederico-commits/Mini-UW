# Productor condicional de operación y NOI sintéticos

T19 produce NOI desde partidas explícitas de ingreso efectivo y gasto operativo sin impuesto, declaradas para la misma moneda, período y base de devengo. Es un perfil matemático acotado de M2, no el motor completo de operación ni una política fiscal adoptada. No construye rentas, vacancia, concesiones, AMI, utility allowance o gastos desde planos y contratos reales.

El contrato `miniuw.synthetic-operating-noi.v1` exige contexto SYNTHETIC, perfil expreso, inventarios, metadatos y supuestos del cálculo. Cada importe conserva valor racional, unidad, moneda, período, base de devengo, referencia declarada y ubicación JSON. Identidades de partidas duplicadas se rechazan; importes iguales con identidades distintas no se eliminan. La exclusividad económica de esas partidas y sus fuentes sigue sin validación independiente.

## Relación matemática implementada

La definición candidata de `docs/model-operations-contract.md`, M2-06/M2-07 y cierre algebraico, se conserva con línea y hash:

```text
A = ingresos efectivos declarados - gastos operativos declarados sin impuesto
N = A - max(F, k*N)
N = min(A-F, A/(1+k))
T = A-N
```

El perfil exige F total no negativo, k fijo, adimensional y no negativo, sin otras ramas o ajustes fiscales. Reporta rama comparable, proxy o igualdad y verifica residual exacto de la ecuación original. Un NOI negativo se conserva; igualdad de ramas no introduce un desempate financiero. No se aplican tolerancias ni redondeos.

F y k son parámetros aportados en el JSON sintético. No se derivan de millage, exención, cap, assessment ratio o norma legal. Su presencia no acredita elegibilidad ni legalidad fiscal. Otros regímenes, k variable, ajustes o coeficientes fuera del dominio no se resuelven con este perfil.

Un k cero explícito es válido y difiere de k ausente. Un inventario vacío no se convierte en cero; hace falta una partida cero explícita si eso es lo que declara la fuente. Moneda/período incompatibles, fuente declarada ausente, unidad incorrecta o base de caja en lugar de devengo bloquean los resultados afectados. Puede conservarse A calculado aunque falte el parámetro fiscal y N/T queden pendientes.

La aritmética tiene límites técnicos de cantidad de partidas y tamaño racional. Si se exceden, no se entrega un NOI incompleto como calculado. Estos límites son recursos de cómputo, no rangos financieros aprobados.

## Evidencia y recuperación

`produce_operating_noi(raw)` devuelve un resultado inmutable con totales, N/T, rama, residual, fuentes y bloqueos. `save_operating_noi` y `load_operating_noi` archivan fuente/resultado y reproducen con código y documentos compatibles. La captura es transaccional local; una falsificación con hash actualizado se rechaza. Las bases runtime quedan fuera de Git y del respaldo documental.

Ejemplo sintético: ingresos 1.450, gastos sin impuesto 250, F=100 y k=1/5 producen A=1.200, N=1.000 y T=200. Con F=300, N=900 y T=300. Sin k, N y T permanecen pendientes. Son cantidades ficticias de un período declarado, no resultados de un deal.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 tools/demo_synthetic_operating_noi.py
```

21 pruebas nuevas comprueban ramas, igualdad, signo, cero/ausencia, sustitución en la ecuación original para una grilla de casos, compatibilidad, inventarios, exclusividad de identidades, fuente literal, presupuesto racional, aislamiento y archivo/reapertura/falsificación/rollback. No son auditoría financiera independiente, los 36 casos de aceptación originales ni cierre de M2. La decisión operacional continúa PENDIENTE.
