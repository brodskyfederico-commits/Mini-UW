# Si invierto USD 10, ¿cuánto cobro y cuándo?

Continuación: [C69–C72, deuda permanente, capacidad y caja por USD 10 en D262](workbook-permanent-sensitivities-D262.md).

D261 conecta los cambios de C66, C67 y C68 en una misma corrida reproducible del perfil sintético D200. C66 modifica la valoración de refinanciación; C67, el precio bruto de venta; C68, el porcentaje de costo de venta sobre ese precio. Cada cambio se ejecuta por separado y luego se recalculan los tres juntos. La valoración y la capacidad disponible no se cuentan como efectivo del inversor.

## Alcance y origen de los valores

Se conserva el equity inicial documentado del proyecto de prueba, USD 2.400.000, y el factor fijo `10 / 2.400.000`. Los aportes adicionales y los cobros se mantienen brutos, fechados y separados. No corresponde al 1101 ni a One Hollywood, ni reemplaza los criterios de Lorena. El retorno personal conserva PENDING sin términos de reparto documentados.

El ensayo principal suma **un punto básico** a cada campo: C66 pasa de 9,50 % a 9,51 % en Base y de 11,50 % a 11,51 % en Downside; C67, de 8,75 % a 8,76 % y de 10,50 % a 10,51 %; C68, de 4,00 % a 4,01 % y de 7,00 % a 7,01 %. Son variaciones declaradas para probar conexiones, no supuestos de mercado adoptados ni umbrales nuevos.

| Corrida | Aporte inicial | Aportes adicionales | Cobros totales | Caja sin recuperar al vender |
|---|---:|---:|---:|---:|
| Base original | 10,000000 | 4,867042 | 18,059354 | 0,000000 |
| Base sólo C66 | 10,000000 | 4,867042 | 18,059354 | 0,000000 |
| Base sólo C67 | 10,000000 | 4,867042 | 18,037335 | 0,000000 |
| Base sólo C68 | 10,000000 | 4,867042 | 18,057345 | 0,000000 |
| Base conjunto | 10,000000 | 4,867042 | 18,035328 | 0,000000 |
| Downside original | 10,000000 | 8,189342 | 6,076704 | 12,112638 |
| Downside sólo C66 | 10,000000 | 8,189342 | 6,076704 | 12,112638 |
| Downside sólo C67 | 10,000000 | 8,189342 | 6,068567 | 12,120775 |
| Downside sólo C68 | 10,000000 | 8,189342 | 6,075784 | 12,113557 |
| Downside conjunto | 10,000000 | 8,189342 | 6,067648 | 12,121693 |

Importes en USD por USD 10 iniciales. Se calcula con fracciones exactas y se presenta con seis decimales; el saldo sin recuperar es caja hasta el cierre, no certificación de pérdida económica final. El dictamen real sigue PENDING.

### Fechas de la corrida conjunta

| Movimiento | Base | Downside |
|---|---:|---:|
| Aporte inicial · 30/03/2027 | 10,000000 | 10,000000 |
| Aporte · 30/06/2027 | — | 0,762275 |
| Aporte · 30/09/2027 | 4,655375 | 0,035729 |
| Aporte · 30/12/2027 | 0,052917 | 7,034046 |
| Aportes · 30/03, 30/06 y 30/09 de 2028 | 0,052917 cada fecha | 0,071458 cada fecha |
| Aportes · 30/12/2028 y 30/03/2029 | — | 0,071458 cada fecha |
| Cobro neto de refi | 2,846667 · 30/09/2028 | 2,445833 · 30/03/2029 |
| Cobro de operación | 1,431058 · 30/12/2028 | 0,549690 · 30/06/2029 |
| Cobro neto de venta, incluida la reserva liberada | 13,757603 · 30/12/2028 | 3,072125 · 30/06/2029 |

El aporte operativo explícito es cero y permanece en los eventos auditados. En el conjunto, el valor de refi del proyecto es USD 4.630.974,547469 en Base y USD 2.191.475,649797 en Downside; esos valores no son distribuciones. La venta bruta es USD 4.816.688,904110 y USD 2.204.834,338725; los costos totales de venta son USD 203.149,225055 y USD 154.558,887145, respectivamente.

## Conexiones y ecuaciones verificadas

```text
Valor de refi = NOI de valoración / C66
Límite LTV = valor de refi × LTV máximo documentado
Capacidad = mínimo de los límites aplicables LTV, DSCR y debt yield
Precio bruto = NOI forward de salida / C67
Costo de venta = precio bruto × C68 + costo fijo declarado
Cobro neto de venta = precio bruto − costos − principal cancelado + reservas liberadas
Cambio de cobro por USD 10 = cambio de cobro del proyecto × 10 / equity inicial
```

Las bases de NOI, el impuesto del comprador y sus ventanas se conservan. C66 no cambia el NOI bancario ni el de valoración; cambia el divisor y el límite LTV. Tampoco modifica automáticamente la solicitud fija de USD 1.400.000 de refinanciación ni su calendario. Mientras esa solicitud siga dentro de capacidad, el cobro neto de refi conserva su importe. Si el préstamo excede el menor límite, la ruta afectada queda PENDING.

C67 recalcula el precio de venta y el costo porcentual correspondiente. C68 no modifica el precio y conserva el costo fijo de USD 10.000 del proyecto de prueba. Si C68 es cero explícito, el costo porcentual es cero y el fijo sigue aplicándose. El conjunto se recalcula desde los datos; no se suman sus deltas aislados, porque precio y porcentaje interactúan.

## Cobertura, evidencia y pendientes

| Requisito y ubicación | Definición y cálculo afectado | Evidencia de validación | Estado y pendiente |
|---|---|---|---|
| `Inputs!A66:F66` | Cap anual de valoración de refi, positivo y con base documentada | Binding hasta `valuation_and_sale.cell_sources.C66`; valor, LTV y caja; control de cambio del límite activo | Conectado en sintético; evidencia y aprobación real pendientes |
| `Inputs!A67:F67` | Cap anual de salida aplicado al NOI forward de su ventana | Binding, cotejo B08 con rango sintético vigente, precio y costos recalculados | PENDING si falta evidencia o se sale de su alcance |
| `Inputs!A68:F68` | Fracción del precio bruto; inventario completo, costo fijo separado y no superposición | Componentes del productor de costos, fuente de cada costo, cierre y variación exacta del cobro | Cero explícito válido; blanco o inventario sin respaldo, PENDING |
| Capacidad y deuda | Menor límite aplicable, solicitud sin ajuste automático | Conciliación de capacidad con LTV/DSCR/debt yield; control de préstamo excedido | PENDING en la ruta excedida; no se inventa otro préstamo |
| Caja por USD 10 | Equity inicial verificado, aportes brutos, cobros y caja sin recuperar | Conciliaciones D200 de obra, operación, refi y venta; comparación de eventos, no de valuaciones como efectivo | Retorno personal y decisiones reales PENDING |
| Revisión y reproducción | Fuentes y solicitud ligadas a la revisión vigente | B16 reproduce las fuentes guardadas; las citas de los cambios deben llegar al cálculo | Sin despliegue ni aprobación financiera implícita |

El contrato optativo es `miniuw.synthetic-worksheet-sensitivities.v9`, con `schema` y dos `scenarios`, Base y Downside. Cada escenario contiene sólo `changes`, de uno a tres campos, sin duplicados. Cada cambio declara `target_cell`, `operation`, `unit`, `value` racional explícito y `source_ref` sintético. C66 y C67 usan `annual_cap_fraction`; C68, `fraction_of_gross_sale_price`. Las operaciones admitidas son reemplazo, cambio relativo, puntos básicos y puntos porcentuales con su unidad explícita. Se conserva el límite de 48 KiB del JSON del expediente.

Los bindings mantienen el valor y la cita del Excel original junto con el valor propuesto, su fuente y el hash de la solicitud. La variante usa `sha256:<binding>#/resulting_value`. Un campo que no llegue a la base de valoración conserva PENDING con `sensitivity_valuation_basis_not_connected:C66-C68`.

Las pruebas incluyen caps cero/negativos, costo fuera de rango, vacíos `null`, cadena vacía y espacios, ausencia de fuente, unidad incorrecta, inventario incompleto, cita antigua, cap de salida fuera de evidencia y solicitud excedida por menor capacidad. Ningún vacío se convierte en cero. Los caps cero son datos numéricos inválidos para esta fórmula y quedan PENDING antes de dividir. El cero de C68 se respeta.

## Reproducción y límites

Con el runtime de OCR configurado en el VPS, desde la raíz del repositorio:

```bash
OMP_THREAD_LIMIT=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests:tools python3 -m unittest -v test_worksheet_pricing_sensitivities
OMP_THREAD_LIMIT=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests:tools python3 tools/check_worksheet_exit_pricing_D151.py --output /tmp/miniuw-d151
```

Las políticas financieras, los criterios, los originales y los expedientes reales se conservan. La entrega externa del motor sigue siendo un PDF de una página; este archivo es documentación técnica interna. El respaldo excluye credenciales, archivos reales de proyectos/clientes, paquetes generados y registros de ejecución.

Validación completada en el VPS: cuatro pruebas nuevas en 303,889 segundos, con seis cambios individuales y dos conjuntos en el ensayo principal, además de capacidad, evidencia, faltantes y ceros; siete controles unitarios anteriores; quince casos completos D151, diez PENDING esperados. B16 reprodujo la variante D261 como VIGENTE y reprodujo D260 sin diferencias. En el control C66 Base = 5 %, el límite activo pasa de LTV a debt yield y la caja sigue igual; C66 Downside = 12 % deja la refi PENDING por capacidad. Son ensayos sintéticos para comprobar la conexión, no términos recomendados ni criterios adoptados. Esta validación es dirigida y no repite la batería general completa.
