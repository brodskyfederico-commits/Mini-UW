# Mini-UW v1 · Cierre técnico D271

El cierre técnico del alcance expresamente probado está aprobado en el VPS. Se terminaron los cuatro pendientes de implementación detallados abajo y la batería general sobre el código congelado de D270. Dictamen real, retorno histórico y uso productivo siguen PENDING; no se habilita despliegue.

[Informe PDF](review/MiniUW_Cierre_Tecnico_D271.pdf) · [Constancia y cobertura](review/MiniUW_Cierre_Tecnico_D271.json)

## Corte y validación

Código probado: `da4358d594b4717db78a9ab68c1cdaca4de5b70e`. Manifiesto SHA-256: `aa9e8f2357773aa3dab19d0347bb7152a6a9ad993410b33790a72ef965d6cc43`. Copia limpia de 2.086 archivos más el manifiesto, cotejada antes y después. Es una copia de fuentes verificada; no se presenta como un checkout Git. Los 681 archivos Python coinciden con la huella congelada D270.

| Actividad | Resultado | Segundos |
| --- | --- | ---: |
| vacios | 55 campos; 440 vacíos nulos, 98 ceros numéricos respetados y 12 ceros rechazados en campos no numéricos | 223 |
| unitarias | 1.766 pruebas, OK; sin fallos, errores u omisiones | 8808 |
| referencias | 26 suites y 2.087 archivos, originales preservados | 41 |
| integral | D102, flujo integral normal/adverso/límites | 57 |
| aceptacion | D200, 16/16: completo PASS, adverso FAIL, incompleto PENDING, corregido PASS, todos simulados | 280 |
| integridad | Fuentes y copia coinciden al terminar | 4 |

La ejecución completa tardó 9.413 segundos (2 h 36 min 53 s). Es una regresión por versión, no el tiempo de analizar un deal. B16 reproduce cada entrega; B17 verifica la versión. El intento inicial de terminal terminó antes de producir resultados; se preservó aparte y no se contó. La ejecución completa supervisada terminó con código 0 en las seis fases.

## Cobertura de los pendientes técnicos

| Requisito y origen | Definición vigente | Código afectado | Evidencia | Estado y límite |
| --- | --- | --- | --- | --- |
| TEC-01 · Horizonte integrado de cinco años desde estabilización; D252, políticas 15–16; D265, TEC-01 | Duración explícita de años completos, grilla trimestral. Cinco años y alternativa de tres años; sin default automático. | `tools/worksheet_holding_horizon_D266.py`; `tools/worksheet_horizon_fiscal_D267.py` | [MiniUW_Validacion_D266.json](review/MiniUW_Validacion_D266.json); [MiniUW_Validacion_D267.json](review/MiniUW_Validacion_D267.json) | Implementado y cotejado en su contrato. Calendario mensual/irregular y devengo distinto requieren contrato y validación propios. |
| TEC-02 · Sensibilidades aisladas y conjuntas, con Upside informativo; D252, políticas 3 y 18–33; D265, TEC-02 | 15 drivers tipados, fuentes propias, Base preservado, cambios de configuración inventariados. Upside no rescata un Base que no cumple. | `tools/worksheet_scenario_program_D268.py`; `tools/worksheet_variant_evidence_D268.py` | [MiniUW_Validacion_D268.json](review/MiniUW_Validacion_D268.json) | Implementado con parámetros explícitos. Sin autorización de defaults históricos, materialidad ni orden de beneficios fiscales. C14 combinado no se convierte en vacancia física. |
| TEC-03 · Renta regulada: AMI, tope y utility allowance; D252, observación adicional del Input Sheet; D265, TEC-03 | AMI, hogar imputado, fracciones, deducción y unidades conciliadas por ventana anual. Renta cobrada = menor mercado/tope neto; no segunda deducción de servicios en Opex. | `tools/worksheet_regulated_rent_D269.py`; `tools/worksheet_rental_inputs_D140.py` | [MiniUW_Validacion_D269.json](review/MiniUW_Validacion_D269.json) | Implementado anual por unidad. Autenticación de aplicabilidad real. PER SF y cambios dentro de la ventana anual requieren contrato separado; no se infieren beneficios. |
| TEC-04 · Tres TIR de D268 pendientes por recurso numérico; D268, arithmetic_pending_IRR; D269, TEC-04 | Extensión optativa con huella del algoritmo: inventario exacto de raíces positivas y TIR anual acotada sólo si hay raíz única probada. | `tools/worksheet_irr_certificate_D270.py`; `tools/worksheet_integrated_screening_D181.py` | [MiniUW_Validacion_D270.json](review/MiniUW_Validacion_D270.json) | Tres casos resueltos sin cambiar la caja. Raíz múltiple/no demostrada, dato ausente o recurso insuficiente: TIR PENDING; no elegir una tasa favorable. |

Las referencias financieras separadas calculan desde celdas y declaraciones fuente. Son controles de software; la revisión financiera humana tiene su propio carril. D268 coteja 71 rutas de caja; D269, ocho; D270, 28, con 16 TIR certificadas. Son corpus relacionados y no se suman como proyectos independientes. Las tres TIR conocidas de D268 se resolvieron en revisiones que declaran la extensión numérica D270; no se alteraron retrospectivamente las versiones anteriores.

## Flujo, Dots y bots

| Etapa | Acción y salida | Bloqueo |
| --- | --- | --- |
| D01 / B01–B03 · Ingreso y registro | Identificar expediente/revisión, registrar originales y huellas, clasificar páginas y fuentes. | No mezclar fuentes o revisiones; inventario incompleto identifica faltantes. |
| D02 / B04 · 55 campos de planilla | Tipar dato, unidad, celda, escenario, confirmación y aplicabilidad. | Vacío no es cero. N/A necesita alcance explícito. Un cero fuera del dominio se rechaza con motivo. |
| D03 / B05–B09 · Planos, GC, banco y mercado | B05/B06 leen y B07 concilia. B08 aporta evidencia financiera; B09 espera B07 y B08 para cotejar costo/área/alcance. | Ausencia, OCR discrepante, hoja duplicada o área no respaldada bloquean el cálculo dependiente. |
| D04 / B10–B11 · Evidencia oficial | Copia local, cita, fecha, jurisdicción, base y vigencia. M2 separa escolar/no escolar y resets declarados. | Lo sintético prueba el mecanismo; no acredita vigencia ni elegibilidad real. |
| D05 / B12–B14 · Dependencias y cálculo | Programa → renta/NOI → presupuesto/calendario → obra/interés → refi/capacidad → operación/venta → retorno y criterio. | El préstamo elegido no supera el menor límite aplicable. Sin refi conserva sus propias fuentes y vencimiento. |
| D06 / B15 · Informe del deal | Cuatro rutas Base/Downside con/sin refi; aportes, cobros brutos, fechas, saldo sin recuperar, múltiplo, TIR y CoC aplicable por USD 10. | Base = aporte inicial verificado; aportes posteriores se muestran separados. Retorno personal necesita reparto documentado. |
| D07 / B16–B17 · Auditoría y calidad | B16 reconstruye fuentes/cálculo/PDF y comprueba vigencia antes de entregar. B17 corre la batería por versión. | Falso verde y revisión anterior bloquean entrega. Una prueba sintética no aprueba una inversión. |
| Carril humano · Responsabilidad y autorización | Custodio de evidencia, revisor financiero, responsable de criterios y aprobador con identidad/alcance acreditados. | Sin firmas y evidencia aplicables, dictamen real e histórico PENDING; despliegue deshabilitado. |

Unidades/superficies → renta y costos → NOI por base → TDC → calendario → desembolsos/intereses → refi y capacidad → operación/deuda/reservas → venta neta → caja del equity → múltiplo/TIR/CoC/criterios. El factor es `10 / aporte inicial verificado`; aportes adicionales y cobros brutos conservan sus fechas. No se presenta el equity agregado como retorno personal sin reparto.

El [catálogo integral D250](MiniUW_Informe_Integral_D250.md) conserva los procesos, los 55 campos y las fórmulas del corte histórico. Los contratos D266–D270 y esta constancia describen los cambios posteriores. Los registros de recuperación y las validaciones anteriores conservan su estado y fecha propios: no se reescriben como si ya hubieran probado el código actual.

## Pendientes que necesitan definición, evidencia o autorización

| ID | Falta | Efecto |
| --- | --- | --- |
| POL-01 | GBA derivado, materialidad y autoridad de fuente | El área no respaldada bloquea los cálculos dependientes |
| POL-02 | Beneficios fiscales condicionales y stress de incertidumbre/orden de reglas | El perfil actual no acredita un beneficio o excepción fiscal real |
| POL-03 | Criterios por versión, RLV por estrategia, equity bajo y precedencia con faltantes | Conservar banda PENDING y no adoptar propuestas ni umbrales históricos sin alcance confirmado |
| PIL-01 | Fuentes y términos reales, roles y cotejo independiente del caso | Datos no documentados quedan vacíos/PENDING; retorno personal requiere reparto real |
| VAL-01 | Validación empírica del OCR, backtest y corridas en paralelo | Las pruebas sintéticas no certifican cero falsos verdes en documentos reales |

Los calendarios mensuales/irregulares, devengo diferente del contrato trimestral, renta regulada PER SF y cambios dentro de una ventana anual requieren contrato, implementación y validación separados. No se convierten ni promedian silenciosamente. No se declaran cerradas todas las 33 políticas. Las propuestas de defaults, autoridad de fuentes, materialidad, beneficios fiscales y precedencia de dictamen permanecen sin activar. Se conserva la banda PENDING decidida por el usuario.

Para el piloto real hacen falta documentos del proyecto, términos, criterios con alcance vigente y responsables/autorización acreditados. El equipo del proyecto aporta los hechos; el responsable de criterios confirma las reglas. El retorno personal necesita reparto real. La validación empírica de los bots, backtest de 3–5 proyectos y 2–3 corridas paralelas siguen pendientes. Los ensayos sintéticos no acreditan cero falsos verdes en cualquier documento real.

## Reproducción

Con Python, las dependencias y OCR indicados en la constancia, desde el commit probado:

```bash
PYTHONPATH=src:tests:tools python3 -m unittest discover -s tests -v
PYTHONPATH=src:tests:tools python3 tools/check_worksheet_blanks_and_zero_D171.py
python3 tools/check_reference_package.py
PYTHONPATH=src:tests:tools python3 tools/check_integral_miniuw_D102.py
PYTHONPATH=src:tests:tools python3 tools/check_worksheet_technical_acceptance_D200.py --output /tmp/miniuw-d200-nuevo
PYTHONPATH=src:tests:tools python3 tools/check_worksheet_irr_certificate_D270.py /tmp/miniuw-d270-nuevo
```

Los directorios de salida deben ser nuevos. Las dependencias de terceros se agregan al PYTHONPATH como ruta absoluta si no están instaladas en el entorno. El último verificador incluye la ruta conjunta AMI/M2/TIR en `joint-AMI/current/package`, con los cuatro flujos; sólo genera ejemplos sintéticos. El perfil requiere parámetros y fuentes explícitos, sin transformar el fixture en defaults de un proyecto.

GitHub conserva código, pruebas, fixtures sintéticos y documentos de este hito. Se excluyen credenciales, tokens, datos vivos de clientes, runtimes, paquetes de ejecución y logs completos. El recibo local de publicación registra el SHA remoto completo, la comparación exacta y las exclusiones; no se afirma éxito de GitHub Actions.
