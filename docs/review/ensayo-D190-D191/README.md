# Si invierto USD 10, ¿cuánto cobro y cuándo?

**Ensayo sintético D191 del paquete D190. Piloto real PENDING.** Los importes corresponden al equity agregado del proyecto antes de impuestos personales. Ambos escenarios parten de un aporte de USD 10 el 30/03/2027.

| Por USD 10 de aporte inicial | Base | Downside |
| --- | ---: | ---: |
| Aportes adicionales, con fechas en la planilla | USD 4,87 | USD 8,19 |
| Cobro neto de refi | USD 2,85 el 30/09/2028 | USD 2,45 el 30/03/2029 |
| Cobro operativo | USD 1,43 el 30/12/2028 | USD 0,55 el 30/06/2029 |
| Cobro neto de venta | USD 13,78 el 30/12/2028 | USD 3,08 el 30/06/2029 |
| **Cobro total** | **USD 18,06** | **USD 6,08** |
| Ganancia o déficit nominal | +USD 3,19 | −USD 12,11 |
| **Sin recuperar al cierre** | **USD 0,00** | **USD 12,11** |

Los totales se calculan antes de redondear. Los cobros y aportes simultáneos se registran en filas separadas. El retorno personal sigue PENDING por falta de términos de reparto.

- [Planilla D190 completada con el ensayo](MiniUW_Cotejo_Sintetico_D191.xlsx)
- [Informe del motor de una página](MiniUW_Informe_USD10_D191.pdf)
- [Resultado reproducible y huellas de insumos](MiniUW_Verificacion_D191.json)
- [Paquete vacío para el primer piloto real](../piloto-real-D190/README.md)

## Verificación en el VPS

1. Se usó el expediente sintético D181 con dos XLSX, un plano, un PDF de evidencia y la revisión designada. Primero se reconstruyó la referencia D179 directamente desde los XLSX y el JSON del caso. Luego se corrió el motor y B16 volvió a auditar el expediente desde sus bytes guardados.
2. El cálculo independiente cuadró en **734 líneas exactas** y sus dos intervalos de TIR quedaron dentro de los del motor. En esas líneas se incluyeron los 23 movimientos fechados de Base y Downside. Se cotejaron además dos aportes de refi explícitamente en cero.
3. Se completó una copia de D190 con las fuentes, fechas, montos en USD del proyecto y por USD 10, y los 20 estados por métrica y escenario. Las 16 reglas presentes son las del fixture D181. Las cuatro filas SRC-02 y SRC-03 siguen PENDING con sus umbrales vacíos. Las 11 filas de responsables reales siguen PENDING.
4. Se comprobó que un importe ausente deje la diferencia vacía, que un cero explícito de aporte se conserve y que un desvío de USD 0,10 quede PENDING. La designación de otra revisión dejó el expediente ensayado como histórico y su estado corriente PENDING. Se verificaron las fórmulas y celdas de la planilla mediante el XML y se reabrió el PDF de una página.
5. La planilla original de D190 conservó su huella. El paquete real queda a la espera de datos y evidencias de Lorena, criterios vigentes, responsables designados y cotejo firmado.

El ensayo usa las bases de cálculo del perfil D181 y sus criterios sintéticos. La aprobación de las bases y reglas reales se registra al recibir el expediente. El alcance de v1 sigue según D189.

## Reproducción

Usá [el entorno OCR fijado](../../workbook-plan-scan-D131.md) y las dependencias de referencia del repositorio. El script vuelve a generar y auditar el ejemplo y escribe la planilla y el PDF en la carpeta indicada.

```sh
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_pilot_intake_D191.py --output /tmp/miniuw-d191
```
