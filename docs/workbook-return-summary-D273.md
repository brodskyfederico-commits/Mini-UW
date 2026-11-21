# D273 · T1 · TIR, primer recupero y pico de equity

Se incorpora la primera tarea de la devolución profesional `MiniUW_Instrucciones_Codex_D273.md`. El contrato nuevo es `miniuw.synthetic-native-rental-inputs.v36`. Envuelve un expediente fiscal v34/v35 completo sin modificar sus celdas, fuentes ni criterios. Las rutas anteriores mantienen sus cálculos y PDF. Se requiere una definición explícita del resumen; no hay valores financieros por defecto.

## Qué cambia y qué no cambia

`results.json.return_summary.scenarios` conserva Base/Downside, cada uno `with_refinance` y `without_refinance`. Cada ruta incluye `irr_annual`, `payback_date`, `payback_reason`, `peak_equity`, `project_peak_equity`, fechas del pico y conciliación acumulada por fecha. Se conserva el ledger bruto original, la normalización por el aporte inicial y las ventanas del expediente. El resumen no usa un umbral de inversión y no cambia la caja, el NOI, el TDC, la capacidad o el dictamen del expediente base.

El PDF de v36 muestra TIR, fecha del primer recupero, pico de equity, aportes/cobros/saldo sin recuperar/múltiplo, caja bruta por año y las fechas de compra, estabilización/refi y venta. El detalle completo, incluidos ceros explícitos, queda en el expediente. Es una salida nueva; no se altera el renderer archivado D266/D267. Los rótulos visibles son españoles y no se presenta un PASS/FAIL como dictamen externo.

## Fórmulas y límites

- `C(t)` = suma de aportes brutos hasta cada fecha; `D(t)` = suma de cobros brutos hasta esa fecha.
- Primer recupero = primera fecha con aporte inicial positivo verificado y `D(t) >= C(t)`. Si no existe: fecha nula y «capital no recuperado en el horizonte». No es una fecha cero.
- Un recupero temprano puede revertirse ante un aporte posterior; el resumen lo informa mediante `recovery_reversed_after_first_payback`. No se lo presenta como recupero permanente garantizado.
- Pico de equity por fecha = `max(0, max_t(C(t) - D(t)))`. Se agregan todos los movimientos de una misma fecha antes de medir. No se inventa un orden intradía. El pico intradía requeriría otro calendario.
- Los importes anteriores están expresados por USD 10 iniciales. Pico del proyecto = pico normalizado / factor, donde factor = `10 / aporte inicial del proyecto verificado`.
- La TIR usa la definición numérica explícita D270. Se muestra su intervalo anual certificado. Varias raíces o raíz no probada mantienen TIR PENDING; no se publica la aproximación mencionada en la devolución como si fuera una prueba.
- La grilla debe cubrir todos los trimestres del horizonte fiscal. Quitar a la vez un trimestre de fechas y movimientos no permite afirmar recupero o pico: se conserva PENDING, sin completar ese hueco con cero.
- Una base ausente/no positiva, importe vacío, fuente ausente, tipo/moneda incompatibles, evento duplicado o totales inconciliables bloquean el resumen afectado. Un cero numérico explícito válido se respeta.

## Revisión y B16

El caso v36 lleva `baseline_case` y `return_summary`. El snapshot incorpora la huella de todo el caso base y la definición del resumen en el rol de fuentes financieras. Cambiar esa definición sin una nueva revisión no habilita caja ni entrega. B16 reconstruye el mismo expediente desde sus archivos fuente y compara el paquete byte por byte. El exportador vuelve a comprobar expediente y revisión antes de escribir el PDF. La traza de pipeline usa la huella del caso v36, y B15 usa la del PDF nuevo realmente generado; la huella del caso base se conserva por separado. El verificador coteja esas referencias con los bytes de case.json y MiniUW_Resumen.pdf, además de reproducir los cálculos. El perfil sigue sin despliegue ni decisiones reales.

El verificador nuevo `check_worksheet_return_summary_D273.py` reconstruye las fórmulas desde las celdas y declaraciones originales del control AMI/M2. El saldo acumulado esperado se calcula desde esos movimientos de referencia antes de observar el ledger o el resumen del motor. Coteja pico, fechas de empate, primer recupero/reversión y extremos de la TIR en las cuatro rutas. No deriva las expectativas de las salidas nuevas.

## Resoluciones de la devolución

El usuario confirmó expresamente el 20/11/2026 conservar todos los criterios aplicables conjuntamente en RLV; la exclusión simultánea YoC/spread de T12 no se adopta. Las cifras financieras independientes no dependen de umbrales, pero un RLV de la casa sí depende de ellos: se mantiene separado y PENDING sin definición adoptada. C51 es LTC, C52 tasa de obra y C53 comisión; un shock de tasa no cambia LTC/comisión. Las fronteras propuestas en T2 son matemáticas, no criterios de inversión.

El registro de las catorce tareas y sus dependencias está en `review/MiniUW_Registro_Revision_D273.json`. La tarea T1 no declara ejecutadas T2–T14. Se agrega además un control parcial de T12 por la decisión del usuario: `miniuw.synthetic-joint-applicable-rlv-scope.v1` declara expresamente YoC y spread juntos y todas las nueve métricas Base no RLV. La búsqueda conjunta D230 ya evalúa ambos; se conserva el contrato histórico con etiqueta única y se permite una declaración nueva coherente con la política confirmada. Ocho pruebas nuevas cotejan cada límite de forma independiente, ambos activos a la vez, criterios faltantes, cero explícito y ausencia de cambios en caja. Esto no completa todavía el enchufe estricto/permisivo ni adopta criterios. La batería completa de cierre y compatibilidad se registra por separado; una prueba dirigida aprobada no se presenta como la batería general.

## Reproducción

```bash
PYTHONPATH=src:tests:tools python3 -m unittest -v test_worksheet_return_summary
PYTHONPATH=src:tests:tools python3 tools/check_worksheet_return_summary_D273.py /tmp/miniuw-d273-nuevo
```

Se requieren las dependencias y OCR del entorno documentado, y un directorio de salida nuevo. Se conservan las cuatro rutas por USD 10 con datos sintéticos, criterios sin adoptar y retorno personal PENDING sin términos de reparto.

## Precisión y rutas parciales

Se leen racionales de hasta 1.300 dígitos por componente, como el protocolo de caja/TIR del motor. La amortización exacta con una tasa estresada puede superar 256 dígitos aunque el importe monetario sea ordinario; se conserva su valor exacto, sin redondear para calcular. Un racional que excede el protocolo o es inválido conserva PENDING. Un año fuera del horizonte de una ruta se rotula «Fuera de horizonte», no como cero; un hueco dentro del calendario sigue bloqueado.

El control se amplía a 18 pruebas del resumen, incluidas una combinación explícita D268 reproducida desde sus fuentes, cotejo financiero independiente, refi Downside PENDING por capacidad, conservación de la caja sin refi y exportación B16 vigente. También se prueban fracciones válidas de más de 256 dígitos y años fuera del horizonte. Las ocho pruebas del alcance conjunto del RLV permanecen separadas. Pasaron las 26 dirigidas y el CLI canónico con la traza corregida; el cierre general debe probar el corte final, sin reutilizar intentos interrumpidos.

## Cierre de validación D273

La ejecución completa del corte congelado pasó 1.792 pruebas unitarias sin errores, fallos ni omisiones, las 26 suites de referencia, la verificación integral y la aceptación D200 16/16. Los once perfiles v25–v35 se reprodujeron desde las mismas fuentes bajo el código anterior probado y el nuevo: todos sus archivos coinciden byte por byte. Se cotejaron los 2.103 archivos listados del corte, más su manifiesto, y los 686 archivos Python quedaron sin cambios durante la corrida. El PDF versionado coincide con el que se regeneró desde fuentes. La constancia distingue el corte de código probado de las adiciones documentales posteriores. T1 queda validado en datos sintéticos; el registro mantiene T12 parcial y las otras tareas pendientes.
