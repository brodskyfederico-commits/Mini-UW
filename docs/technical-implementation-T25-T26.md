# De la operación calculada al cobro del inversor

T25 conecta un NOI sintético reproducido con cobros/pagos mediante ajustes de devengo y saldos de trabajo. Después concilia una asignación propuesta de caja entre deuda, inversiones, reservas, aportes, distribución y saldos retenidos. T26 lleva únicamente los importes conciliados a movimientos vacíos expresamente vinculados del ledger del inversor, y recalcula ganancia, múltiplo y TIR con T23–T24.

La distribución es una propuesta suministrada, contrastada contra caja: no se determina como todo el residual ni se autoriza por cuadrar. El perfil abarca un período declarado; continuidad entre períodos, liquidez intraperíodo, condiciones bancarias y derecho a distribuir siguen pendientes.

## Ejemplo sintético y significado para el inversor

| Etapa | Importe ficticio |
|---|---:|
| Ingreso efectivo devengado | 1.450 |
| Gastos operativos devengados sin impuesto | 250 |
| Impuesto condicional calculado | 200 |
| NOI | 1.000 |
| Cobros operativos tras ajustes y saldos | 1.390 |
| Pagos operativos tras ajustes y saldos | 435 |
| Caja operativa | 955 |
| Caja libre antes del reparto propuesto, tras otros movimientos | 510 |
| Distribución operativa propuesta | 100 |
| Caja libre retenida al cierre | 410 |
| Caja restringida al cierre | 230 |

El ejemplo declara caja inicial libre 50 y restringida 100; paga principal 200, interés 100, fees 5, inversión 50 y otros pagos 10; deposita 150 en reservas y libera 20. Aporte adicional y otros cobros son cero expresos. Las transferencias de reservas no se suman como ingreso ni se tratan como distribución.

Los 100 distribuidos se incorporan al movimiento operativo vacío de 2027-12-31. Sobre la base inicial explícita de 1.000 normalizada a 10, ese movimiento representa un cobro de 1. El resto del ledger conserva aporte inicial 10, refi 5, otro cobro operativo 1 y venta 9, produciendo cobros 16, ganancia 6 y EM 1,6x. Sólo el primer reparto operativo se conecta aquí al productor de caja; refi, venta y segundo reparto siguen siendo importes suministrados. La caja retenida no se añade a esos cobros.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 tools/demo_operating_cash_returns.py
```

## Devengo frente a caja

Con Δ como cierre menos apertura, el contrato existente establece:

- Cobros = ingreso efectivo − ingreso sin caja − Δcuentas por cobrar + Δingresos anticipados.
- Pagos = gasto operativo + impuesto − gasto sin caja − Δcuentas por pagar + Δgastos anticipados.
- Caja operativa = cobros − pagos.

`reconcile_operating_cash` reproduce primero el NOI desde sus bytes originales y verifica hashes de fuente/ejecución, contexto, moneda y referencia de período. Exige fechas, referencia de base temporal, inventario declarado completo y referencia de clasificación sin superposición entre gastos NOI y usos de financiación/inversión. Esta referencia y la declaración no acreditan clasificación o completitud financiera.

Cada una de las cuatro familias de saldos exige apertura y cierre no negativos, fuente, moneda y corte `OPENING:`/`CLOSING:`; no hay cero automático. Los ajustes sin caja admiten signo explícito. Los cobros/pagos calculados se comparan exactamente con sus afirmaciones suministradas: una diferencia bloquea el reparto. Importes brutos de caja negativos requieren otro perfil, conservando el cálculo y la causa.

## Asignación de caja y reservas

Caja libre previa + caja operativa + otros cobros no financieros + liberación de reservas + aportes − principal − interés − fees − capex − otros pagos − depósito de reservas = caja libre antes de la distribución propuesta.

Se resta el reparto propuesto y se compara el resultado con la caja libre de cierre declarada. En paralelo, reserva inicial + depósito − liberación debe igualar la reserva final declarada. La conciliación total elimina transferencias internas; también se verifican ambas cuentas por separado para que errores opuestos no queden ocultos.

Todos los usos y fuentes requieren importes, incluidos ceros, moneda/período y referencia. Caja libre o restringida negativa bloquea; no se reduce el reparto, agrega capital, libera reserva ni crea deuda para cerrar una diferencia. Un faltante en asignación puede conservar la caja operativa calculada, pero impide exportar aporte y distribución. El saldo libre positivo no equivale a capital aún invertido, valor de equity ni monto legalmente distribuible.

La deuda pagada/proyectada se suministra por principal/interés/fees: no se infiere de un servicio anual equivalente o vencimiento. No se comprueba aún su correspondencia con el calendario contractual, pago efectivo, permisos de reserva o covenants. El perfil excluye proceeds de refinanciación/venta; no es el productor de liquidación de esos cierres.

## Enlace con retornos y recuperación

`assemble_operating_returns` requiere hashes exactos del ledger original, especificación y ejecución de caja. Reproduce la cadena NOI/caja antes de consumirla. Sólo rellena un importe vacío de una distribución operativa con fecha/moneda/contexto coincidentes; no cambia criterios, supuestos, otras cifras o movimientos ya poblados. El evento conserva procedencia al hash y JSON Pointer exactos de la salida de caja.

Si hay aporte adicional positivo, exige su propio movimiento bruto vacío `additional_capital`; no lo compensa contra el reparto. Aporte cero sin slot adicional no genera un evento ficticio. Una fecha fuera de la cuadrícula no se traslada. Cualquier otro dato requerido ausente en el ledger conserva PENDING en T23, aunque este enlace haya compilado.

Los nuevos paquetes locales capturan fuentes, NOI, caja, binding y compilación de forma transaccional. Al reabrir, verifican bytes, versiones, documentos y reproducción completa. La demostración reabre ambos paquetes y verifica su enlace. Sus transacciones son separadas; no se afirma atomicidad entre bases, publicación o infraestructura. El paquete T26 reproduce el NOI compilado suministrado; el productor residencial anterior necesita su paquete T22 enlazado, como comprueba una prueba de integración.

## Evidencia y pendientes

24 pruebas T25 y 18 T26: 42 nuevas, 502 técnicas en total. Incluyen identidades calculadas independientemente, separación NOI/caja/reparto, saldos, reservas, aportes, continuidad de evidencia, datos faltantes, diferencias compensadas, fechas, límites aritméticos, rechazo de resultados alterados con hash nuevo, rollback y recuperación. Una prueba une renta residencial → NOI → caja → movimiento → retornos conservando el enlace de ambos paquetes.

Faltan continuidad y caja de toda la tenencia, presupuesto/financiación de construcción, productores de refinanciación y venta, conciliación de deuda pagada frente a obligaciones, LP/JV/waterfall e impuestos aplicables, riesgos/sensibilidades y PDF final integrado. Las declaraciones sintéticas no sustituyen revisión profesional. No se dan por ejecutados los 36 casos financieros originales ni los 56 escenarios de diseño D02/D03. Decisión PENDING; sin despliegue o cierre financiero.
