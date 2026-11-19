# D260 · C61–C62, impuesto inmobiliario, NOI y caja

## Si invierto USD 10, ¿cuánto recibo y cuándo?

Ejemplo exclusivamente sintético del perfil D200, normalizado sobre USD 2.400.000 de equity inicial del proyecto: factor fijo `10 / 2.400.000`. No corresponde al 1101 ni a One Hollywood. El retorno personal sigue PENDING sin términos de reparto documentados.

Se prueba C61 de 80 % a 81 % en Base y de 90 % a 91 % en Downside —un punto porcentual— y C62 de USD 1.900 a USD 1.919 y de USD 1.300 a USD 1.313 por unidad comparable/año —1 % relativo—. Son cambios declarados para las pruebas; no son valores recomendados ni criterios de Lorena. Cada cambio se corre por separado y luego ambos juntos contra el mismo original.

| Escenario y corrida | Aporte inicial | Aportes adicionales | Cobros totales | Caja sin recuperar al vender |
|---|---:|---:|---:|---:|
| Base original | 10,000000 | 4,867042 | 18,059354 | 0,000000 |
| Base sólo C61 | 10,000000 | 4,867042 | 18,059354 | 0,000000 |
| Base sólo C62 | 10,000000 | 4,867042 | 18,057296 | 0,000000 |
| Base C61 + C62 | 10,000000 | 4,867042 | 18,057296 | 0,000000 |
| Downside original | 10,000000 | 8,189342 | 6,076704 | 12,112638 |
| Downside sólo C61 | 10,000000 | 8,189342 | 6,074943 | 12,114399 |
| Downside sólo C62 | 10,000000 | 8,189342 | 6,076704 | 12,112638 |
| Downside C61 + C62 | 10,000000 | 8,189342 | 6,074943 | 12,114399 |

Los importes son USD por USD 10 iniciales, calculados sin redondeo intermedio y presentados con seis decimales para hacer visible el efecto fiscal. La caja sin recuperar compara todos los aportes con los cobros hasta el cierre; no certifica una pérdida económica final. El dictamen real conserva PENDING.

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
| Cobro de operación | 1,429000 · 30/12/2028 | 0,547929 · 30/06/2029 |
| Cobro neto de venta, incluida la reserva liberada | 13,781629 · 30/12/2028 | 3,081180 · 30/06/2029 |

Los ceros explícitos de aporte operativo se conservan en los eventos del expediente. La refinanciación solicitada sigue fija en USD 1.400.000: recalcular capacidad no modifica automáticamente el préstamo ni genera un cobro nuevo.

## Qué se conecta y qué base usa

El contrato optativo `miniuw.synthetic-worksheet-sensitivities.v8` admite uno o dos cambios explícitos de C61–C62. Usa la política sintética D150 ya declarada, con sus fuentes, tasas, unidades, alcance y período. No adopta una regla fiscal legal ni una exención, ni modifica el perfil estatutario D203.

Para cada ventana de doce meses del propietario:

```text
F = C62 × unidades comparables documentadas
k = C61 × tasa anual sobre valor fiscal / cap de la estimación fiscal
B = ingresos netos antes del impuesto inmobiliario
NOI = min(B − F, B / (1 + k))
Impuesto = B − NOI = max(F, k × NOI)
Residual = B − Impuesto − NOI = 0
```

Se comprueban operación, banco y valoración de refi de forma independiente. En el ensayo principal, el piso comparable domina la operación de Base; la estimación sobre valor fiscal domina el banco y la valoración de Base y las tres ventanas de Downside. Por eso C61 puede cambiar capacidad sin cambiar el cobro operativo en Base, mientras que C62 puede cambiar su piso sin afectar el impuesto pagadero en Downside. Los datos y sus citas se recalculan aunque no cambie el importe.

| Ventana de la corrida conjunta | Impuesto Base del proyecto | NOI Base del proyecto | Impuesto Downside del proyecto | NOI Downside del proyecto |
|---|---:|---:|---:|---:|
| Operación | 49.894,000000 | 401.945,100000 | 46.164,787800 | 228.287,412200 |
| Banco | 50.735,263751 | 417.574,187249 | 47.339,533217 | 234.096,592833 |
| Valoración de refi | 53.437,721678 | 439.816,639322 | 50.914,015017 | 251.772,601733 |

La venta del perfil D200 usa el impuesto del comprador declarado para su ventana forward: USD 75.000 en Base y USD 70.000 en Downside, separados en escolar/no escolar. Esa evidencia, sus fechas y su fuente permanecen intactas al variar C61–C62. Por eso el precio y el cobro neto de venta no cambian aquí. C61–C62 no reemplazan esa retasación. El modelo D150 anterior, que declara la misma base fiscal para sus cuatro ventanas, conserva su comportamiento original.

El NOI bancario alimenta DSCR y debt yield; el NOI de valoración alimenta el valor y el límite LTV. Se aplica la menor capacidad. La caja de operación deduce el impuesto una vez, antes de deuda y depósito de reserva. `operating_noi_after_reserve` identifica el NOI de esa misma ventana menos el depósito de reposición, sin mezclarlo con las bases bancarias o de valoración.

## Contrato, evidencia y bloqueos

La solicitud conserva `schema` y dos `scenarios`, Base y Downside; cada uno contiene sólo `changes`. Cada cambio exige `target_cell`, `operation`, `unit`, `value` racional explícito y `source_ref` sintético. C61 usa `fraction_of_market_value`; C62, `USD_per_comparable_unit_per_year`. Se admiten reemplazo y cambio relativo, y puntos porcentuales o básicos sólo sobre la fracción C61. No se aceptan celdas repetidas, vacíos, N/A como número ni una tasa sin unidad.

Las fuentes de las celdas cambiadas apuntan al hash de su binding y a `/resulting_value`; las demás mantienen la cita del Excel. El control exige que esa cita llegue efectivamente a la evidencia fiscal. Si otra rama de impuestos ignora esos campos, la variante queda PENDING con `sensitivity_property_tax_basis_not_connected:C61-C62`.

| Requisito o variable y ubicación | Definición vigente en este perfil | Módulo afectado y evidencia de validación | Estado y pendiente |
|---|---|---|---|
| `Inputs!A61:F61` | Razón valor fiscal/valor de mercado, entre cero y uno; tasa anual y cap fiscal separados, documentados | `worksheet_property_tax_D150.declared_property_tax`; prueba de cálculo independiente, fuentes, rango y cero explícito | Conectado en sintético; base y evidencia del deal real pendientes |
| `Inputs!A62:F62` | Impuesto anual del comparable por unidad del alcance declarado; piso por conteo verificado | D150 y M2; prueba aislada, conjunta y de cambio de rama | Conectado en sintético; comparable real y alcance pendientes |
| Capacidad de refi | Menor límite bancario, sin ampliar automáticamente la solicitud | `worksheet_sensitivities_D253`; caso C62 Downside = USD 3.000/unidad/año bloquea caja por capacidad | PENDING si el préstamo excede el límite |
| Caja por USD 10 | Factor sobre equity inicial verificado, aportes y cobros brutos fechados | Conciliación D200 de obra, operación, refi y venta; ecuación exacta de la diferencia de impuesto/caja | Calculable sólo con las fuentes y la capacidad completas |
| Revisión y entrega | B16 reproduce el expediente contra revisión vigente externa | Auditoría del paquete completo y compatibilidad de D259 | El dictamen real conserva PENDING; sin despliegue |

Las pruebas cubren el cambio de piso a estimación y el inverso, ambos valores en cero —impuesto cero sólo en las ventanas donde ésa es la base aplicable—, ausencia de tasa, fuente, conteo o cap fiscal, valores negativos o fuera de rango y capacidad excedida. Un cero de C61 por sí solo no elimina el piso; un cero de C62 por sí solo no elimina la estimación. Si falta C62 en la variante, el cambio C61 válido puede seguir calculado, pero el conjunto y su ranking quedan PENDING. Si falta la fuente fiscal Base, no se inventa su caja ni se retira la información válida de Downside.

## Reproducción

Con el runtime de OCR disponible en el VPS, desde la raíz del repositorio:

```bash
OMP_THREAD_LIMIT=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests:tools python3 -m unittest -v test_worksheet_tax_sensitivities
OMP_THREAD_LIMIT=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests:tools python3 tools/check_worksheet_property_tax_D150.py --output /tmp/miniuw-d150
```

Los originales, las políticas financieras abiertas, los criterios de inversión y los expedientes reales se conservan. La entrega externa del motor sigue siendo un PDF de una página; este registro es documentación técnica interna. El respaldo del hito excluye credenciales, datos reales, paquetes generados y registros de ejecución.

Verificación completada en el VPS: cuatro pruebas nuevas, con cuatro cambios individuales y dos conjuntos en el ensayo principal, más cambios de rama, cero, faltantes y capacidad; seis controles unitarios anteriores; catorce casos completos D150, nueve PENDING esperados; B16 reprodujo tanto la variante D260 vigente como D259 sin diferencias. La batería nueva tardó 227,922 segundos. Son verificaciones dirigidas; la batería general completa no se repitió en D260. La aceptación técnica de los sintéticos no habilita decisiones reales.
