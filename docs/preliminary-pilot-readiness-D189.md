# Si invierto USD 10, ¿cuánto cobro y cuándo?

En el piloto sintético D188, Base aporta USD 6,22 adicionales y cobra USD 31,29 hasta el 30/12/2028. Downside aporta USD 8,01 adicionales, cobra USD 10,15 hasta esa fecha y deja USD 7,86 sin recuperar. El [PDF de una página](review/MiniUW_Preliminar_Obra_Etapas_D188.pdf) desglosa los flujos fechados de equity agregado, antes de impuestos personales.

## Alcance v1 congelado

El Mini-UW v1 cubre el filtro residencial temprano y la evaluación formal del mismo tipo de proyecto. Incluye la planilla Base/Downside, el cotejo de documentos en los formatos ensayados, obra, deuda, refinanciación, operación, venta, retorno por USD 10, dictamen y auditoría. **PRELIMINAR** queda incluido como ruta de LOI para priorizar revisión, con el dictamen formal siempre PENDING. Los ajustes de validación, datos y corrección del piloto están dentro del v1. Nuevos productos, estrategias o módulos se registran para una versión posterior o Full UW. El libro Full UW se incorpora cuando esté disponible para el traspaso.

El corte funcional se apoya en D181–D184 para el expediente integrado y en D185–D188 para PRELIMINAR. El congelamiento deja pendientes las aprobaciones y la aceptación real.

## Mínimos verificados del ranking sintético

Se verifica el perfil residencial financiado con desembolsos por etapas del [caso D188](workbook-preliminary-staged-D188.md). Requiere los dos escenarios del mismo deal y la misma fecha de corte y grilla trimestral. Cada archivo tiene huella declarada. En los ensayos de comparación D185, las oportunidades deben compartir también la ruta de financiación. La convención sintética ordena por múltiplo de equity de Downside y da la misma posición a empates. Su aplicación real sigue pendiente de aprobación.

| Requisito para ingresar | Ubicación | Evidencia y efecto del faltante |
| --- | --- | --- |
| Identidad, fecha y bases | Inputs B3, E3, C7 y C34, y huella de cada XLSX en el caso | Omitir identidad, fecha, base, huella o libro retira la caja del escenario y excluye el deal. |
| Renta y operación | C8–C11, C13–C15, C57–C60, C62, C75 y C76 | Cada celda numérica mínima se probó vacía por separado. Cero numérico válido es una entrada explícita. |
| Adquisición, obra, cronograma y venta | C32–C33, C35, C37–C40, C42, C46–C47 y C67–C68 | Se prueban omisiones una por una. El respaldo aporta alcance, unidades, estacionamientos, absorción y tratamiento de reservas al vender. |
| Financiación | C51–C53 y C66, C69–C74. El complemento incluye principal, compromiso, plazos, H02, H08, debt yield aplicable, fondeo de refi y disposición de reserva permanente. | La ausencia de un mínimo o una solicitud superior al menor límite aplicable deja PENDING. |
| Etapas de obra | `support.financing.construction_stages` por escenario | Cada fila requiere fecha, participación elegible, fracción solicitada, disponibilidad, fuente, fecha de evidencia y responsable. Se bloquean excesos de disponibilidad o compromiso. |
| Trazabilidad de supuestos | `support` de programa, costos, renta/gastos, calendario, financiación y salida | Cada grupo requiere fuente, fecha compatible con el corte, responsable y descripción. La prueba retira grupos y campos por separado. |

Las 212 variantes bloqueadas verifican que se retire la caja afectada, se conserve la del escenario independiente, se excluya el deal del ranking y el PDF mantenga **Dictamen formal PENDING**. Se reproduce el paquete completo tras restituir un cero explícito. Las pruebas se ejecutan en el VPS con datos sintéticos y la salida es de una página. [Matriz de casos y bloqueos](review/MiniUW_Verificacion_D189.json).

## Corrida de referencia

```sh
PYTHONPATH=src:tests python3 tools/check_preliminary_pilot_readiness_D189.py
PYTHONPATH=src:tests python3 tools/check_worksheet_preliminary_stages_D188.py --output /tmp/miniuw-piloto
PYTHONPATH=src:tests python3 tools/miniuw_worksheet_v1.py audit /tmp/miniuw-piloto
```

Para revisar las entradas, usar el [caso JSON](../templates/synthetic-preliminary-staged-D188.json), [Inputs Base](../templates/synthetic-preliminary-staged-base-D188.xlsx) e [Inputs Downside](../templates/synthetic-preliminary-staged-downside-D188.xlsx) de D188. El paquete de salida conserva los dos XLSX, el caso, el PDF, los resultados y el manifiesto de huellas.

## Habilitación del primer piloto real

| Pendiente | Evidencia para cerrar |
| --- | --- |
| Autoridad y roles | Custodio de evidencia oficial, responsable de criterios y revisor financiero designados. |
| Definiciones y criterios | SRC-02 y SRC-03 aprobados, criterios vigentes por escenario y política de ranking para el uso real. |
| Expediente autorizado | Base y Downside de Lorena, supuestos y documentos vigentes del caso, con autorización para procesarlos. |
| Validación de punta a punta | Cotejo independiente de caja y dictamen por escenario, con diferencias resueltas o documentadas y revisión sobre la versión reproducida. |

Un piloto puede completarse con un PENDING o FAIL explicado y reproducible. El paso de un deal a Full UW requiere PASS vigente y aprobación auténtica, conforme al [contrato de decisión](decision-input-contract.md).
