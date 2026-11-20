# D270 · TIR con prueba exacta de unicidad, sin cambiar la caja

Se cierran las tres TIR del corpus D268 que quedaban PENDING por el presupuesto del aislador anterior: Downside con refi de los drivers 18, 28 y 29. El método optativo prueba una única raíz admisible y acota la TIR anual. No cambia rentas, costos, impuestos, deuda, criterios, aportes o cobros. El dictamen real y el histórico siguen PENDING.

Fuente del pendiente: `MiniUW_Validacion_D268.json`, `arithmetic_pending_IRR`; registro `MiniUW_Alcance_y_Pendientes_D269.json`, TEC-04. Implementación: `worksheet_irr_certificate_D270.positive_inventory/annual_enclosure/verify_cash`; conexión: callback optativo de `worksheet_integrated_screening_D181.collect_metrics/screen_integrated` y rama sin refi de D140. Los casos que no declaran esta extensión mantienen el método anterior y sus resultados reproducibles.

## Definición matemática

Para flujos netos trimestrales documentados `c[t]`, se busca `z > 0` tal que:

`P(z) = Σ c[t] × z^t = 0`.

La TIR anual efectiva es `z^(-4) − 1`. Es una tasa derivada de los movimientos; no se introduce una tasa de descuento mensual ni un retorno objetivo.

La regla de Descartes se aplica a dos transformaciones exactas:

- `(1+t)^n × P(t/(1+t))` cubre `0 < z < 1`.
- `P(1+t)` cubre `1 < z < infinito`.
- `P(1) = 0` se comprueba por separado.

Cero o una variación certifican el número de raíces del intervalo correspondiente. Si el inventario completo prueba una sola raíz admisible, se construye un intervalo racional y se verifican los signos del VAN en sus extremos. Todos los cálculos usan fracciones exactas. Se conserva la precisión de 68 bisecciones del camino trimestral existente; los presupuestos computacionales son explícitos y acotados.

Si esta condición suficiente no resuelve el inventario, el aislador existente puede aportar su prueba. Un inventario incompleto, varias raíces, un polinomio idénticamente nulo, ausencia de una raíz admisible o agotamiento del recurso deja TIR PENDING. No se selecciona una tasa favorable entre varias. Una TIR exactamente cero puede publicarse sólo cuando está probada; no equivale a un dato vacío.

## Contrato y bloqueos

`rent_inputs.irr_certificate` declara perfil, reglas, referencia de definición y SHA-256 del algoritmo. La extensión pertenece a los perfiles fiscales integrados v34/v35. El código cargado, el archivo y la definición deben coincidir; cambiar el código en disco o los presupuestos en memoria no conserva una aprobación anterior.

Cada fecha de la grilla necesita movimientos observados, incluido el cero explícito. Una fecha omitida, un importe vacío, un tipo de movimiento desconocido, otra moneda o una grilla incompatible deja PENDING. La definición ausente no activa el método viejo como default. Los límites anteriores del lector permanecen vigentes; v34 con esta extensión utiliza el límite existente de 96 KiB, y v35 conserva su límite de 256 KiB.

El verificador no satisface una falta de criterio o evidencia. D219/D220 siguen retirando la caja no respaldada antes de formar el dictamen y entregar el PDF. El retorno personal necesita términos de reparto documentados. No se activa ninguna propuesta de política financiera.

## Validación ejecutada

Se reprodujeron los datos financieros congelados de los tres casos D268, usando las mismas cinco fuentes financieras y de criterios. Cada control conserva la TIR anterior PENDING; su nueva revisión analítica agrega únicamente la definición numérica y la referencia correspondiente. Los doce relatos de caja de esas revisiones coinciden byte por byte con sus controles: cada aporte, cobro, importe, fecha, base y referencia financiera. También coinciden NOI, financiación y capacidad.

| Downside con refi | Antes | Ahora, TIR anual acotada |
|---|---|---|
| Driver 18, renta residencial | PENDING por recurso del aislador | −16,48 % a −16,47 % |
| Driver 28, seguro | PENDING por recurso del aislador | −16,28 % a −16,27 % |
| Driver 29, impuesto operativo | PENDING por recurso del aislador | −16,47 % a −16,46 % |

El cotejo independiente verifica las fórmulas desde celdas y padrones hasta la venta, los movimientos por USD 10 y los extremos de TIR. Una corrida conjunta con AMI/M2 aporta otras cuatro rutas: sus cajas coinciden con las publicadas en D269, con 130 hechos críticos verificados.

Pasaron 13 pruebas unitarias, incluidas tasas negativas, cero exacto, dos/tres raíces admisibles, flujos nulos, movimiento faltante frente a cero, unidades/grilla, definición ausente, límites de tamaño/recurso y cambios de código o reglas. La cadena completa mantiene PENDING al quitar un criterio o el respaldo del DSCR. La entrega se limita al expediente vigente de una página.

## Reproducción

```bash
python3 -m unittest discover -s tests -p test_worksheet_irr_certificate.py -v
python3 tools/check_worksheet_irr_certificate_D270.py /ruta/a/un/directorio/nuevo
```

El fixture numérico versionado se usa sólo para pruebas. El modelo requiere declaración explícita de la extensión; no altera retrospectivamente las revisiones guardadas. La evidencia está en `MiniUW_Validacion_D270.json`. Esta mejora matemática no certifica las 33 políticas, un documento real ni una inversión. Sin despliegue ni decisiones reales.
