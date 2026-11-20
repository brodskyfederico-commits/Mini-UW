# D268 · Sensibilidades desde fuentes hasta caja por USD 10

Se implementa un ejecutor único de variantes con planillas y respaldos propios, sin cambiar los criterios ni el aporte inicial. Cada expediente conserva aportes y cobros brutos fechados, Base/Downside y venta con/sin refi. Los parámetros de este ensayo son sintéticos: no son valores por defecto, propuestas aprobadas ni datos de un proyecto real.

## Cobertura y fórmulas

Fuente de requisitos: matriz D251, p. 1 política 3, p. 2 políticas 18–26 y p. 3 políticas 27–33; cotejo preservado en `worksheet-policy-implementation-audit-D252.md`, tabla «Matriz por política». Código: `worksheet_scenario_program_D268.DRIVERS/driver_terms/transformed/check_variant/run_program`.

| Política | Entrada y transformación explícita | Recálculo y respaldo exigido |
|---|---|---|
| 18 | C8–C11 × (1 + cambio relativo) | Renta residencial, pérdidas, NOI, capacidad y cuatro retornos; rango de mercado vigente del ensayo. |
| 19 | C16–C18 × (1 + cambio relativo) | Ingreso comercial NNN y NOI. No se cambia superficie ni unidades. |
| 20 | C14 + puntos porcentuales / 100 | Pérdida residencial combinada, conforme a la definición de C14. No se infiere vacancia física sin desglose. |
| 21 | C19 + puntos porcentuales / 100 | Vacancia comercial e ingreso reconocido. |
| 22 | C35, C37 y C38 × (1 + cambio relativo) | Obra vertical, parking y sitio; contingencia, soft costs, fondeo e intereses. La nueva cotización GC debe coincidir con C35 y su base documentada. |
| 23 | C46 + meses enteros | TCO, calendario de desembolsos, intereses, impuestos previos, estabilización, venta y ventanas forward. Perfil trimestral explícito. |
| 24 | C47 + meses enteros | Déficit de lease-up, calendario y primer año estabilizado; absorción y fechas respaldadas. |
| 25 | C52 + pb / 10.000 | Interés de obra sobre desembolsos y saldo; nuevos términos bancarios coincidentes. |
| 26 | C69 + pb / 10.000 | Cuotas, saldo, DSCR, capacidad y cobros. El principal solicitado permanece documentado. |
| 27 | C66 + pb / 10.000 | Valoración de refi y límite LTV con su propia base de NOI. |
| 28 | C59 × (1 + cambio relativo) | Prima, gastos, NOI y caja; se exige cotización y población asegurada concordantes. |
| 29 | Impuesto operativo/forward M2 × (1 + cambio relativo) | Ajuste posterior al padrón, una sola vez; no cambia millage, retasación ni impuesto previo a estabilización. Sólo alcance sin beneficios fiscales condicionales. |
| 30 | C71 + puntos porcentuales / 100 | Menor límite bancario aplicable. No se aumenta ni reduce automáticamente el préstamo para producir PASS. |
| 31 | C67 + pb / 10.000 | Venta a partir del NOI forward y costos de cierre; evidencia de cap compatible. |
| 32 | C75 + puntos porcentuales / 100 | Renta por aniversario, NOI, venta y flujos. No se incorpora una tasa de descuento. |

Cada driver declara aplicabilidad, unidad, cambios Base/Downside y fuente. Una excepción necesita fuente y motivo; un valor ausente no se interpreta como cambio cero. El cero explícito se conserva. La variante conjunta se deriva del mismo origen que las individuales, sin acumular involuntariamente los ensayos anteriores. Si el origen ya declara un stress fiscal, el cambio relativo adicional se compone multiplicativamente.

`check_variant` comprueba las 55 celdas, el inventario de ajustes de configuración y las huellas de cada paquete. Rechaza cambios ajenos en criterios, geometría, compromiso bancario, esquema de aportes, bases de costo o supuestos de fondeo. Cada fuente complementaria debe pasar después los lectores y las conciliaciones existentes. Cambiar un hash declarado no autentica un documento.

## Ingreso y auditoría

El perfil optativo v34 agrega `Independent_Reference.json` a las cinco fuentes existentes. Intake registra sus bytes y los liga al caso y a la revisión vigente. La referencia se prepara desde fuentes y fórmulas separadas; el ejecutor no la genera a partir de sus resultados para hacerlos coincidir. Los perfiles históricos conservan sus referencias y contratos.

`worksheet_variant_evidence_D268.reference_issues` exige inventarios completos de escenarios, banco, mercado, planos y M2. D267 coteja las ventanas contra las duraciones literales del Excel. No se puede eliminar un campo crítico del inventario para convertir un faltante en verde. D219/D220 retienen el bloqueo de caja y entrega ante citas faltantes, diferencias o falsos verdes.

Upside es informativo. No sustituye el dictamen de Base/Downside. `cash_deltas` muestra diferencias en aportes brutos, cobros y caja sin recuperar sobre la misma base inicial. Conserva las fechas y no inventa una tasa de descuento ni un ranking económico. Una ruta ausente o con otra base deja su comparación PENDING.

## Prueba ejecutada y límites observados

- 18 expedientes en una corrida: origen, 15 individuales, conjunto y Upside. Cada paquete se reprodujo con B16.
- El OCR rechazó la revisión sintética del conjunto por confianza insuficiente y diferencias de lectura. Sus cuatro rutas quedaron PENDING y el PDF no se entregó. Se preservó ese expediente.
- Una nueva revisión con identificador legible pasó 120 controles críticos. Se volvió a ejecutar únicamente el conjunto, con alcance de ejecución explícito. Downside supera el DSCR: refi PENDING, préstamo sin redimensionar y venta sin refi calculable.
- El cotejo independiente verifica **71 rutas de caja** entre los 19 expedientes y mantiene cinco rutas sin caja por sus bloqueos. Coteja presupuesto, usos, deuda, capacidad LTV/DSCR/debt yield, seis NOI por escenario, venta y movimientos por fecha. Las tres TIR no convencionales que exceden el recurso del aislador actual permanecen PENDING; no se publica una raíz aproximada como certificada.
- Pasaron 11 pruebas unitarias del contrato, vacío/cero, unidades, cambios conjuntos, diferencias de caja, inventarios incompletos, falsos verdes y préstamo por encima de capacidad. La entrega vigente del conjunto corregido se probó; expediente sin respaldo y revisión anterior quedaron bloqueados.
- B16 reprodujo el expediente D267 y su PDF sin cambios. Esta es validación dirigida; no sustituye la próxima batería general de la versión consolidada ni la validación con documentos reales.

La salida de una página usa el renderer fiscal D267 preservado; su encabezado identifica ese productor. Presenta Base refi: USD 5,14 adicionales y USD 27,83 cobrados; Base sin refi: USD 5,14 y USD 28,27. Downside refi queda PENDING por capacidad; sin refi: USD 8,68 adicionales, USD 7,93 cobrados y USD 10,76 sin recuperar. Cada importe se expresa por USD 10 iniciales; el PDF y el JSON conservan fechas y movimientos. Redondeo sólo de presentación. No son retornos históricos ni personales.

## Reproducción

Con el runtime OCR/JPEG y las dependencias del repositorio:

```bash
python3 -m unittest discover -s tests -p test_worksheet_scenario_program.py -v
python3 tools/check_worksheet_scenario_program_D268.py /ruta/a/un/directorio/nuevo
```

Para fuentes ya preparadas, `worksheet_scenario_program_D268.py programa.json --sources directorio --output directorio_nuevo` ejecuta el programa. `--case combined` limita explícitamente la ejecución; los demás casos no se presentan como ejecutados. Intake v34 usa `--include-reference` al registrar y correr las seis fuentes. Los resultados incluyen hashes, cotejo, eventos por USD 10 y diferencias respecto del origen.

Pendientes separados: activar shocks requiere política aprobada; C14 no acredita un desglose físico; el devengo mensual/irregular y los beneficios fiscales condicionales no se deducen del contrato trimestral. Renta regulada, decisiones de autoridad/materialidad y certificación empírica siguen en el registro de pendientes. Dictamen real, histórico y retorno personal sin reparto documentado: **PENDING**. Sin despliegue.
