# D269 · Renta regulada, NOI y retorno por USD 10

El perfil optativo v35 conecta límites de renta explícitos con las cinco anualidades desde estabilización, el año forward de venta, NOI, capacidad, refi y caja con/sin refi en Base y Downside. No acredita elegibilidad legal ni incorpora un beneficio fiscal. Las 55 celdas nativas conservan su estructura: C8–C11 siguen siendo rentas de mercado; la restricción regulatoria se documenta como fuente suplementaria.

Fuente del requisito: D251 p. 3, observación de renta asequible; `worksheet-policy-implementation-audit-D252.md`, sección «Observación adicional del Input Sheet». Productor: `worksheet_regulated_rent_D269.configuration/project_window`. Conexión: `worksheet_rental_inputs_D140.rental_noi/run_rental_scenario`. Auditoría: `worksheet_regulated_rent_D269.validate_reference/critical_fields` y D219/D220.

## Entradas y fórmulas vigentes del perfil de prueba

Cada escenario aporta distribución de unidades reguladas y de mercado por tipo, conciliada con la población del modelo; referencia al déficit neto de lease-up declarado; y una ventana documentada por anualidad, incluida la de salida. Cada ventana indica vigencia y si sus valores son observaciones o pronósticos sintéticos. No se copian límites al año siguiente por ausencia de datos.

Para cada tipo regulado se declaran: tamaño de hogar imputado y su fuente; ingreso AMI anual; fracción de límite de ingreso; proporción de ingreso aplicable a renta; utility allowance mensual del inquilino; unidades monetarias y fuentes. La moneda es USD y cada magnitud declara unidad. No se incorporan automáticamente una proporción del 30 %, un porcentaje AMI ni una regla de hogar por dormitorio.

| Cálculo | Definición | Control |
|---|---|---|
| Tope bruto mensual | AMI anual × fracción de ingreso × proporción para renta / 12 | Cada operando tiene unidad, valor y fuente. |
| Tope neto al propietario | Tope bruto − utility allowance mensual | Si es negativo, PENDING. No se recorta a cero. |
| Renta regulada cobrada | Menor entre renta de mercado proyectada y tope neto | La selección es una regla explícita del perfil, con su fuente; no una aprobación legal. |
| Renta de mercado proyectada | C8–C11 × factor anual documentado de C75 | El crecimiento se aplica una vez. El tope de cada año es independiente. |
| Ingreso bruto del tipo | 12 × (unidades reguladas × renta regulada + unidades de mercado × renta de mercado) | La suma de unidades coincide con el grupo. |
| Renta efectiva por unidad antes de pérdidas | Ingreso bruto / (12 × unidades totales) | Grupo vacío con cero explícito: N/A documentado, sin dividir por cero. |
| NOI y retorno | El ingreso anterior alimenta pérdidas, concesiones, gestión y el motor financiero existente | Utility allowance no se vuelve a restar de gastos del propietario. M2, reservas y deuda mantienen sus contratos. |

El alcance actual es `PER UNIT`. Un `PER SF` sin conversión regulatoria documentada queda PENDING. Los límites deben cubrir toda la ventana anual; un cambio regulatorio dentro del período requiere un contrato específico y no se aproxima silenciosamente. Exenciones, density bonuses, elegibilidad Live Local y cualquier beneficio condicionado quedan fuera de este cálculo.

## Evidencia de implementación

- Pasaron 10 pruebas unitarias: fórmula conocida, mezcla de unidades, crecimiento por encima del tope, valores vacíos frente a cero explícito, unidad monetaria incorrecta, falta de fuente/vigencia/año forward, población inconsistente, tope negativo, límites de tamaño de fuente y falsos verdes.
- El flujo completo v35 pasó 130 hechos críticos por expediente: los 116 del caso fiscal más fuente y seis ventanas de renta regulada por escenario. Alterar el tope de un grupo retiene la caja de ese escenario. Omitir el cap forward del inventario no produce verde.
- Se corrieron dos controles equivalentes: cuatro unidades reguladas con fuentes sintéticas y cero unidades reguladas con N/A explícito. Se cotejaron ocho rutas de caja, operación, deuda, capacidad, venta, múltiplo y extremos de TIR con fórmulas separadas que leen las fuentes.
- La diferencia de NOI frente al control coincide exactamente con la menor renta × (1 − pérdidas − concesiones) × (1 − gestión). Eso comprueba que no se duplicó la deducción de servicios ni se alteró el impuesto para otorgar un beneficio.
- Los dos expedientes pasaron B16 y la revisión vigente. Se entregó la hoja de una página del ensayo regulado. La ampliación del límite de JSON a 256 KiB pertenece sólo a v35; los límites anteriores permanecen vigentes para sus perfiles.

Por USD 10 iniciales, el ensayo regulado aporta USD 4,78 adicionales en Base y USD 8,13 en Downside. Los cobros Base son USD 28,31 con refi y USD 28,32 sin refi; Downside cobra USD 8,34 y USD 8,35 y deja USD 9,79 y USD 9,78 sin recuperar, respectivamente. Estabilización/refi: 01-01-2028 y 01-07-2028; venta: 01-01-2033 y 01-07-2033. La hoja detalla los aportes y cobros trimestrales. Estos valores provienen de una propuesta bancaria sintética de USD 1 M y supuestos declarados; no son condiciones de Lorena ni datos históricos de un deal.

## Reproducción y transición

```bash
python3 -m unittest discover -s tests -p test_worksheet_regulated_rent.py -v
python3 tools/check_worksheet_regulated_rent_D269.py /ruta/a/un/directorio/nuevo
```

El verificador compara el fixture versionado, arma las seis fuentes, ejecuta ambos controles, coteja los cálculos y entrega el PDF vigente. El productor no lee el template para rellenar datos de un caso. Sin un valor o regla mínimos, se conserva PENDING.

Para un proyecto real hacen falta las fuentes y la aplicabilidad del programa, los hogares/unidades afectados, los límites y deducciones vigentes, y la aprobación del responsable de criterios y supuestos. Un nombre de fuente o un hash no autentica esa aprobación. El dictamen real, el histórico y el retorno personal sin reparto documentado siguen **PENDING**. No hay despliegue ni certificación de las 33 políticas.
