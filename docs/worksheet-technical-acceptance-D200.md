# Mini-UW v1 · Aceptación técnica sintética en el VPS

Por cada **USD 10 iniciales** de equity agregado, la corrida completa calcula aportes adicionales y cobros fechados en Base y Downside. La decisión real y el retorno personal quedan **PENDING**.

## Evidencia de los cuatro hitos de D197

| Hito | Evidencia ejecutable |
| --- | --- |
| 13 · Expediente desde archivos | D198 lee los dos XLSX de entradas, el XLSX de criterios, el plano y el PDF de respaldos. Separa el registro de huellas del armado. El expediente se deriva sin editar su JSON. Con una revisión anterior, cambiar Downside C70 bloquea la caja de Downside e identifica el archivo y la celda. El mismo conjunto de archivos y registro reproduce el expediente byte a byte. |
| 14 · Deuda, salida y corte fiscal | D199 usa la misma entrada y la caja auditada. Prueba un trimestre de solo intereses, primera amortización y liquidación al vender. También prueba la venta con la deuda de obra vigente hasta su vencimiento. Un ensayo de obra cruza el 1 de enero de 2028: tasación sintética del terreno y de las partes utilizables al corte, con tasas escolares y no escolares declaradas. Una fecha faltante deja la variante PENDING. |
| 15 · Criterios y RLV | El perfil v31 requiere un único umbral de rendimiento para la grilla, YoC o spread, y verifica base y ventana de los criterios que consumen NOI. Quitar un FAIL de equity/TDC en cualquiera de los escenarios bloquea el RLV. Una revisión corregida lo recalcula. Downside puede tener un PASS explícito sin FAIL en una métrica ajena al RLV. |
| 16 · Aceptación de punta a punta | B16 reproduce el expediente completo, adverso, incompleto y corregido. La batería compara las líneas de NOI, deuda, venta y retorno con D179. Comprueba fuentes y usos por fecha y saldo de caja libre y restringida. LP más GP concilian por fecha bajo términos sintéticos de D169. La frontera PASS del RLV y la frontera FAIL tienen vecinos verificados por separado. La ocupación física queda PENDING si C14 carece de desglose. |

[Plan de aceptación D197](review/MiniUW_Cierre_Tecnico_y_Piloto_D197.md) · [Resultado de la batería](review/MiniUW_Verificacion_D200.json)

## Resultado por USD 10 iniciales

| Escenario | Aporte adicional | Refinanciación | Operación y venta | Total cobrado | Sin recuperar |
| --- | ---: | --- | --- | ---: | ---: |
| Base | USD 4,87 | USD 2,85 · 30/09/2028 | USD 15,21 · 30/12/2028 | USD 18,06 | USD 0,00 |
| Downside | USD 8,19 | USD 2,45 · 30/03/2029 | USD 3,63 · 30/06/2029 | USD 6,08 | USD 12,11 |

[Informe de una página, con aportes y cobros por fecha](review/MiniUW_Informe_USD10_D200.pdf)

El caso completo usa criterios sintéticos para ensayar un PASS. El adverso endurece el umbral de ocupación de Downside y da FAIL. En el incompleto faltan umbrales y da PENDING. El corregido los restituye en otra revisión y vuelve a PASS. Los cuatro conservan la misma caja.

### Calendarios sintéticos del mismo expediente

| Escenario y ruta | Aporte adicional | Total cobrado | Último cobro | Sin recuperar |
| --- | ---: | ---: | --- | ---: |
| Base · Solo intereses y después amortización | USD 4,88 | USD 16,64 | 30/03/2029 | USD 0,00 |
| Downside · Solo intereses y después amortización | USD 8,33 | USD 5,01 | 30/09/2029 | USD 13,33 |
| Base · Venta sin refinanciación | USD 4,87 | USD 18,23 | 30/12/2028 | USD 0,00 |
| Downside · Venta sin refinanciación | USD 8,25 | USD 6,47 | 30/06/2029 | USD 11,79 |

La ruta de amortización cuenta el tramo de solo intereses dentro del plazo original, usa el saldo posterior a la primera cuota amortizante y aplica el DSCR al servicio anual amortizante. El préstamo de USD 1,4 millones excede la capacidad en esa variante Downside. Una solicitud alternativa de USD 1,35 millones permite ensayar el cierre. La venta diferida utiliza NOI de salida y caja intermedia explícitos para sus fechas. El impuesto de obra se paga el 30/03/2028 en el ensayo Downside. De USD 1 millón de terreno y tres mejoras de USD 200.000, 300.000 y 400.000, la base sintética es USD 1,5 millones y la salida de caja es USD 15.000. El calendario de aceptación utiliza tasas de prueba. El módulo fiscal real M2 y la aprobación de criterios del piloto siguen PENDING.

Los flujos alternativos y sus conciliaciones quedan en el expediente. Las comparaciones de dictamen corresponden al caso principal. Cada cálculo se realiza con racionales exactos y el informe redondea la presentación a dos decimales.

## Reproducción

Desde una copia limpia con Python 3.12.3, las dependencias de `requirements-reference.txt` y el binario, idioma y biblioteca OCR documentados en [D162](workbook-evidence-progressive-D162.md):

```bash
PYTHONPATH=src:tests OMP_THREAD_LIMIT=1 python3 tools/check_worksheet_technical_acceptance_D200.py --output /tmp/miniuw-d200
```

La batería prepara las entradas con los respaldos publicados y corre B16 sobre los cuatro expedientes. Si se usa `--output`, elegí un directorio nuevo o vacío. Para el flujo de dos pasos con archivos ya disponibles:

```bash
PYTHONPATH=src python3 tools/worksheet_intake_D198.py register ./fuentes-sinteticas ./registro.json --revision SYNTHETIC-prueba-v1
PYTHONPATH=src python3 tools/worksheet_intake_D198.py run ./fuentes-sinteticas ./registro.json --settings ./templates/synthetic-acceptance-settings-D200.json --output ./Expediente
```

El directorio de prueba contiene `Inputs.xlsx`, `Downside_Inputs.xlsx`, `Criterios_Lorena.xlsx`, `Plan.pdf` y `Evidence.pdf`. El registro conserva hashes de archivo y de celdas para localizar cambios. El archivo de configuración conserva las reglas, las bases de comparación, las confirmaciones y las referencias sintéticas declaradas. La revisión de vigencia del caso se genera al armar el expediente. Las confirmaciones y el registro son evidencias sintéticas locales.

**Alcance de cierre** · D197 mide el checklist técnico v1 con 16 hitos de igual peso. D200 acredita el cierre sintético. El piloto real mantiene sus seis condiciones de cierre y requiere documentos, responsables, criterios y validación del caso.

## Entrega vigente del informe integral

El comando `deliver` vuelve a ejecutar la auditoría B16 desde el expediente, verifica la revisión designada fuera del paquete y coteja su huella justo antes de exportar. Entrega el PDF auditado de una página de los perfiles sintéticos v31 y v32 cuando los flujos por USD 10 de Base y Downside están disponibles. La revisión histórica, una fuente o PDF incompatibles y la caja incompleta bloquean la entrega. Un criterio de inversión pendiente puede dejar el dictamen simulado PENDING con ambos flujos visibles. La decisión real sigue PENDING.

```bash
PYTHONPATH=src:tests python3 tools/miniuw_worksheet_v1.py deliver ./Expediente --current-revision ./Vigente.json --output ./MiniUW_Vigente.pdf
```

Designá la revisión verificada en `Vigente.json` y elegí un destino nuevo fuera del expediente. La constancia incluye la huella del PDF y de la revisión. El ensayo automatizado de D216 usa las fuentes sintéticas de D200 y D203. Coteja la salida completa y rechaza el PDF alterado, la revisión anterior, el reemplazo de la revisión durante la entrega y la caja incompleta.

## Corrección financiera y recálculo para la entrega

D217 corrige el costo porcentual de venta en C68 de 4 % a 5 % en Base y de 7 % a 8 % en Downside, con planillas e inventario sintéticos del perfil v32. El cotejo reconstruye el precio bruto desde NOI de salida y cap, y verifica el efecto exacto `precio bruto × cambio de tasa × 10 ÷ aporte inicial` sobre el cobro de venta. Se cotejan las fechas y los importes de cada aporte y cobro.

| Escenario | Aporte extra por USD 10 | Cobro total anterior | Cobro total corregido | Venta neta corregida | Sin recuperar al cierre |
| --- | ---: | ---: | ---: | --- | ---: |
| Base | USD 4,87 | USD 19,51 | USD 19,30 | USD 14,92 el 30/12/2028 | USD 0,00 |
| Downside | USD 8,19 | USD 7,13 | USD 7,03 | USD 4,01 el 30/06/2029 | USD 11,16 |

La prueba coteja ambas planillas antes y después, verifica el bloqueo por C68 al usar el registro anterior y confirma que el comando `deliver` sólo entrega el PDF auditado de la revisión nueva. La decisión real permanece PENDING.

```bash
PYTHONPATH=src:tests OMP_THREAD_LIMIT=1 python3 -m unittest discover -s tests -p test_worksheet_cash_revision_D217.py -v
```
