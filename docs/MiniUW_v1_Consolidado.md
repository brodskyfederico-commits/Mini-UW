# Mini-UW v1 consolidado con datos sintéticos

Mini-UW v1 reúne una entrada, una corrida local y un resumen de una página para el perfil de obra con desembolsos, transición de la misma deuda a operación, renta residencial por tramos, gastos, tenencia y venta. Cada resultado conserva sus fuentes y bloqueos. La decisión permanece PENDIENTE; la integración no cierra la validación financiera ni adapta por completo la hoja real de Lorena.

## Flujo de información

1. Recibir un único expediente JSON con identidad, revisión, contexto, fuentes declarativas y fecha UTC de evaluación.
2. Indexar los 55 campos originales y los diez criterios nuevos del caso. Mantener faltantes, unidades, períodos y discrepancias visibles.
3. Reconstruir deuda de obra y caja previa a apertura, transición de deuda, NOI, caja operativa, detalle de gastos y renta por tramos. Conciliar continuidad, venta y obligaciones de deuda.
4. Compilar aportes y cobros brutos del equity con fechas. Calcular resultado de caja, EM, todas las raíces/intervalos de IRR y referencia por cada 10 sobre una base explícita.
5. Verificar la vigencia declarada de todas las fuentes antes de mostrar cifras actuales. Comparar sólo métricas y criterios expresamente compatibles.
6. Generar una página de prueba y sus archivos internos. Reproducir el resultado/PDF y comprobar inventario, hashes y texto antes de materializar la carpeta completa.

Los [siete Dots y 17 bots](MiniUW_v1_Dots_y_Bots.md) tienen entradas, salidas, dependencias, bloqueos y estado de implementación en el [contrato verificable](miniuw-v1-dot-bot-contracts.json). Los roles que leen planos o verifican fuentes externas siguen pendientes. Los bots son roles funcionales; esta corrida local no despliega agentes.

## Entrada única

El [ejemplo ejecutable](../templates/miniuw-v1-synthetic-case.json) usa el esquema `miniuw.synthetic-v1-case.v1` y perfil `SYNTHETIC-V1-STAGED-PHASED-RENTAL-HOLD-SALE-v1`. Los números se suministran como racionales exactos, por ejemplo `{"numerator": "10", "denominator": "1"}` según el contrato de cada productor; no se aceptan decimales binarios como sustituto. `null` conserva un faltante y el cero explícito conserva su valor.

| Grupo de entrada | Contenido | Bloqueo |
|---|---|---|
| Identidad | `schema`, `profile`, `case_id`, `case_revision`, `title`, `context` | Identidad sintética/revisión/contexto inválidos o perfil ajeno |
| Alcance temporal | `as_of_UTC`, `required_scenarios` | Falta UTC; escenarios fuera del perfil único; no se copia Base a Downside |
| Formulario original | `original_inputs`, 55 filas en orden original | Valor, mapeo, unidad, período o base faltantes mantienen pendiente la decisión; contradicción con la fuente retira la proyección |
| Criterios | `criteria`, diez filas sin valores heredados | Falta definición/unidad/período/operador/umbral/fuente o hay incompatibilidad/banda |
| Fuentes complementarias | `recipe`, 14 secciones estructuradas | Datos/fechas/inventarios/enlaces económicos incompletos o incongruentes |
| Vigencia | `source_registry`, requisitos, evidencia, hashes, localizadores y fechas | Fuente pendiente, vencida, sustituida, distinta o fuera de contexto |

Cada campo original puede declarar un `recipe_pointer` interno, su valor literal, `unit`, `period_ref` y `mapping_basis_ref`. El mapa verifica igualdad exacta; la semántica financiera sigue sujeta a la definición vigente. El ejemplo vincula 1/55 campos y conserva 54 pendientes. La proyección condicionada utiliza sus fuentes complementarias completas; no demuestra que los 55 campos alimenten el motor ni que una hoja real sea suficiente.

| Sección de recipe | Variables simplificadas |
|---|---|
| `construction_loans` | Desembolsos y fechas; principal; interés por intervalo y comisiones declaradas; vencimiento |
| `preopening_source` | Aportes, adquisición/usos, pagos, caja y saldos de apertura |
| `construction_binding` | Mapa explícito de obligaciones calculadas a eventos suministrados |
| `phase_contract` | Misma obligación en transición, saldo y fecha; términos operativos suministrados |
| `operating_periods` | Fuentes de NOI/caja, unidades/capacidad/disponibilidad, renta/base/área, pérdidas/concesiones, fracción de mes suministrada, gastos/impuestos, pagos/cuentas por pagar/prepagos, deuda/reservas/capex/aportes/repartos |
| `holding_manifest` | Inventario de períodos, fechas y continuidad de saldos |
| `sale` | Proceeds suministrados, deuda, costos, reservas, caja retenida y distribución neta de venta |
| `hold_sale_binding` | Identidad y continuidad de tenencia/deuda/venta |
| `cash_boundary_binding` | Saldos al pasar de obra a operación |
| `window_binding` | Ventana y fuentes de la corrida completa |
| `investor_source` | Eventos brutos separados, fechas, base de normalización, slots explícitos de aportes/cobros y estados de capital |
| `investor_binding` | Mapa de resultados de caja a eventos vacíos declarados, sin duplicar flujos |
| `expense_manifest` | Períodos de gastos que deben conciliar con NOI/caja |
| `rental_manifest` | Períodos de renta vinculados con sus fuentes NOI/caja |

La ruta no tiene refinanciación intermedia. Los módulos previos de refi/capacidad continúan disponibles por separado; el resumen muestra refi/cash-in como pendientes cuando no hay un importe aplicable explícito. No se deduce financiamiento, aprobación bancaria, impuesto aplicable, entrega física o regla de prorrateo por días. El calendario de renta exige fracciones y bases suministradas.

## Salida de una página

La página responde cuánto aporta el equity del proyecto, cuánto cobra y cuándo, su resultado de caja, EM e IRR; muestra base por cada 10, riesgos, diez métricas y bloqueos. El retorno personal necesita términos de asignación. Capital remanente, equity retenido y CoC permanecen pendientes si no están definidos; equity retenido no se suma a cobros.

El ejemplo sintético aporta 1.400 y cobra 778: 200 de operación y 578 de venta, con resultado −622 y EM 389/700. Sobre una base explícita de aportes totales de 1.400, cada 10 equivale a cobros de aproximadamente 5,5571 y resultado −4,4429; no representa una inversión personal. La IRR anual se presenta como intervalo ampliado −58,02% a −58,01%, conservando los intervalos exactos y todas las raíces en JSON.

| Archivo | Función |
|---|---|
| `case.json` | Bytes exactos de la entrada |
| `results.json` | 55 estados, diez métricas/criterios, etapas, retorno actual y bloqueos |
| `execution-evidence.json` | Paquete financiero sintético reproducible o constancia explícita de cálculo bloqueado |
| `MiniUW_v1_Resumen.pdf` | Exactamente una página de prueba |
| `report-manifest.json` | Texto/cifras, coordenadas, referencias y hashes de la página |
| `audit.json` | Reproducción y comprobación técnica; auditoría financiera independiente permanece falsa |
| `bot-execution.json` | Estado ejecutado, parcial, bloqueado o sólo contrato por cada rol |
| `package.json` | Inventario exacto y hashes de los otros siete archivos |

El [ejemplo completo guardado](review/miniuw-v1-example/package.json) permite recuperar la corrida. Una fuente vencida retira las cifras actuales de la página y conserva la evidencia histórica por separado. La salida rechaza desbordes, más de diez eventos, más de tres filas anuales o caracteres incompatibles; no recorta información ni añade otra página.

## Ejecución local

Desde la raíz del repositorio, con Python 3.11 o posterior y las dependencias de `requirements-reference.txt` instaladas:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python tools/miniuw_v1.py run templates/miniuw-v1-synthetic-case.json --output /tmp/miniuw-v1-demo
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python tools/miniuw_v1.py audit /tmp/miniuw-v1-demo
```

Usar una carpeta nueva por revisión. Una repetición idéntica sólo verifica los ocho archivos; una carpeta diferente/incompleta no se sobrescribe. La materialización utiliza una carpeta temporal hermana y renombrado local tras las comprobaciones. No es publicación productiva ni protección entre múltiples publicadores concurrentes.

La carpeta generada debe conservarse completa. El comando `audit` vuelve a ejecutar fuentes y PDF con estas versiones compatibles, además de verificar los hashes. Un caso pendiente puede generar un informe correcto y finalizar técnicamente con código 0; JSON inválido, alteraciones o fallos de representación devuelven código 2 sin publicar una carpeta parcial. Modificar importes exige nueva revisión y evidencia compatible explícita; el modelo no renueva autoridad o vigencia por su cuenta.

## Reglas y pendientes de cierre financiero

- Datos requeridos/reglas faltantes, conflictos o bandas mantienen PENDIENTE; un fallo conocido no oculta otros faltantes.
- Criterios nuevos por caso; ningún umbral histórico se activa por defecto. No se ajustan variables automáticamente para conseguir PASS.
- Unidades, monedas, períodos, definiciones, fuentes y dependencias deben ser compatibles; undefined no se transforma en cero.
- Aportes, deuda y cobros permanecen separados. El mismo flujo se cuenta una vez; valor del activo/equity retenido no es caja distribuida.
- Una cifra actual exige cálculo conciliado y fuentes compatibles al UTC explícito. Una revisión previa no autoriza una nueva.
- Los resultados y el PDF deben reproducirse desde la entrada; la comprobación determinista no equivale a auditoría financiera independiente.
- El alcance sigue sintético, sin despliegue, sin decisiones reales y sin admisión automática a Full UW.

Sólo EM llega como métrica puntual derivada al comparador de esta ruta. IRR conserva intervalos; YoC, spread, recuperación/cash-in de equity, ocupación de equilibrio, CoC pos-refi, equity/TDC y asking/precio soportado conservan sus pendientes específicos en `results.json`. Falta cerrar su definición y conciliación completa, el mapeo semántico de toda la hoja, fuentes auténticas/planos/GC/banco, impuestos aplicables, capital/equity/retorno personal y la aceptación financiera profesional. La ampliación a condominios sigue diferida a Full UW.

La [matriz incremental de cobertura](technical-coverage-T85-T87.json) vincula requisitos, definición, ubicación, módulos, pruebas y pendientes. La matriz histórica de 398 filas y los originales permanecen intactos; nombrar un requisito no lo marca cubierto.
