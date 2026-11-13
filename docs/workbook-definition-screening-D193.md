# Si invierto USD 10, ¿cuánto cobro y cuándo?

El expediente sintético D193 conserva los flujos del equity agregado de D181. El aporte inicial es de USD 10 el 30/03/2027 en ambos escenarios.

| Por USD 10 iniciales | Base | Downside |
| --- | ---: | ---: |
| Aportes adicionales, fechados en el PDF | USD 4,87 | USD 8,19 |
| Cobro neto de refi | USD 2,85 el 30/09/2028 | USD 2,45 el 30/03/2029 |
| Cobro de operación | USD 1,43 el 30/12/2028 | USD 0,55 el 30/06/2029 |
| Cobro neto de venta | USD 13,78 el 30/12/2028 | USD 3,08 el 30/06/2029 |
| **Cobro total** | **USD 18,06** | **USD 6,08** |
| **Sin recuperar después de la venta** | **USD 0,00** | **USD 12,11** |

[Informe sintético de una página](review/MiniUW_Informe_USD10_D193.pdf). El retorno personal y la decisión real siguen PENDING.

## Cálculo y dictamen

| Requisito | Definición candidata y origen | Resultado Base | Resultado Downside |
| --- | --- | ---: | ---: |
| SRC-02 · Ocupación de equilibrio | En la ventana estabilizada de 12 meses, B13 encuentra el porcentaje de renta residencial efectiva que cubre el costo operativo, impuesto, reserva de reposición y servicio amortizante anual con tasa fija. Conserva el ingreso comercial y otros ingresos de ese perfil. Reproduce la base de NOI antes de impuestos. | 32,66 % económica | 69,37 % económica |
| SRC-03 · Valor residual del terreno | B13 prueba la grilla de USD −500.000 a USD 9.400.000 en pasos de USD 10.000. Mantiene fija la deuda y ajusta TDC y equity por Δprecio × (1 + C33). Exige en conjunto YoC con reservas o spread de base comparable, TIR, múltiplo y equity/TDC. | USD 3.200.000 | USD 2.720.000 |
| SRC-03 · Último precio antes de FAIL | Máximo punto de la grilla en PASS o banda. Guarda la prueba inmediatamente anterior y posterior a ambos límites. | USD 7.350.000 | USD 4.140.000 |
| B14 · Precio pedido / RLV | Usa el precio pedido y divide por el RLV positivo. La comparación PASS termina en 1×. El límite FAIL se obtiene de la segunda frontera del mismo cálculo. | 0,3438× | 0,4779× |

El fixture tiene umbrales inventados para ejercitar el circuito, identificados como sintéticos. Incluye Downside en la comparación de RLV sólo para probar la ruta. Su aplicabilidad real sigue por confirmar. El PASS de ensayo pertenece a esos umbrales, aun cuando Downside deja parte del capital sin recuperar. El CoC publicado conserva la definición del tramo de D181. Se ajustaron el YoC y el spread que intervienen en el RLV para que sigan las bases de reservas del ensayo D184. Las valoraciones de banco, refi, salida y todos los flujos del caso se reprodujeron íntegros.

### Bloqueos y evidencia

- La ocupación física requiere un desglose con fuente que reproduzca la renta efectiva del expediente. Con C14 combinado se puede calcular la económica si la regla la pide. Una ocupación física solicitada con desglose ausente o incompatible queda PENDING.
- Una frontera de RLV ausente o abierta en la grilla, una regla faltante, una base de cap incompatible o una aplicabilidad sin confirmar dejan el cociente PENDING. Un límite cero o negativo se conserva en la evidencia cuando la grilla lo encuentra. El cociente queda vacío.
- La banda entre las dos fronteras sigue PENDING. Un umbral manual que contradiga la banda calculada deja la fila PENDING tanto en el dictamen como en el cotejo desde el Excel de Lorena.
- La revisión designada vincula las políticas candidatas y las reglas al expediente. El auditor B16 vuelve a generar el resultado desde las planillas y los PDF. El archivo D181 se reproduce con su perfil original.

SRC-02 y SRC-03 se mantienen como definiciones candidatas hasta su confirmación por el responsable de criterios. El piloto real también requiere criterios aplicables de Lorena y respaldos del caso.

## Reproducción

Configurar [el runtime OCR fijado](workbook-plan-scan-D131.md). El perfil v30 y su revisión están en [caso](../templates/synthetic-workbook-definition-screening-D193.json) y [revisión](../templates/synthetic-workbook-current-revision-D193.json).

```sh
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_definition_screening_D193.py --output /tmp/miniuw-d193
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-d193 \
  --current-revision templates/synthetic-workbook-current-revision-D193.json
```

[Registro de pruebas](review/MiniUW_Verificacion_D193.json) · [Fuente y ensayos de límites D184](workbook-performance-policy-D184.md).
