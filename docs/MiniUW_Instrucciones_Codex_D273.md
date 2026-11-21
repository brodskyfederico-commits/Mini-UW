# Mini-UW v1 · Instrucciones de implementación para Codex · D273

> **Cómo usar este archivo:** colocarlo en `docs/` del repositorio y pedirle a Codex:
> *«Leé `docs/MiniUW_Instrucciones_Codex_D273.md` y ejecutá las tareas en el orden indicado. Respetá las reglas de la sección 0 en cada cambio. Al terminar cada tarea, corré la batería completa y dejá la constancia de validación.»*

**Objetivo del bloque:** dejar el Mini-UW listo para correr un caso real **sin los criterios de Lorena**. Todo lo que es cálculo, datos, presentación y control de calidad queda terminado. Los criterios entran después como un archivo que sólo cambia la columna «Estado».

**Base:** expediente D272 (commit `e332f33f23cf31d00897137322e345b081830297`, código probado `da4358d594b4717db78a9ab68c1cdaca4de5b70e`) y cierre D271.

---

## 0. Reglas que no se rompen (aplican a todas las tareas)

1. **No activar criterios.** No completar `'Criterios PASS FAIL'!E7:H16`, no cambiar `criteria_adopted=False`, no elegir la definición del RLV de la casa, no resolver la precedencia de un FAIL con faltantes, no definir la regla de ranking real. Esos puntos son L01–L07 y quedan PENDING.
2. **No inventar datos ni nombres.** Vacío ≠ cero. No rellenar campos con defaults, promedios ni copias de Base. Los roles se registran con campos vacíos que llena el equipo.
3. **Versionar, no pisar.** Cada contrato nuevo lleva su propio esquema (v36, v37, …). Los perfiles anteriores (v25–v35, D200, D266–D270) tienen que reproducirse **byte por byte** con sus fixtures actuales.
4. **Referencia independiente.** Cada cálculo nuevo tiene un verificador que parte de celdas y fuentes literales, nunca de resultados del motor.
5. **Fronteras matemáticas ≠ criterios.** Los límites de la tarea T2 (múltiplo 1,00x, DSCR 1,00x, cobertura de refi) son fronteras matemáticas. Se rotulan así y no producen PASS ni FAIL.
6. **Sin despliegue y sin acceso externo.** No usar red ni servicios externos y no modificar presupuestos de CI.
7. **Batería completa al cierre de cada tarea:** 1.766 unitarias actuales más las nuevas, las 26 suites, la aceptación D200 16/16 y la preservación de fuentes. Dejar la constancia en `docs/review/MiniUW_Validacion_D27x.json`.
8. **Idioma:** todo lo que ve una persona (PDF, expediente y mensajes de PENDING) va en español. Los identificadores de código pueden quedar en inglés.

---

## Orden de ejecución

| Orden | Tarea | Prioridad |
|---|---|---|
| 1 | T1 · TIR y fecha de recupero en la caja resumida | Alta |
| 2 | T2 · Distancia a la quiebra (fronteras) | Alta |
| 3 | T3 · Grilla de precio y precio máximo con metas configurables | Alta |
| 4 | T4 · Tornado de sensibilidades | Media |
| 5 | T5 · Hoja de decisión de una página | Alta |
| 6 | T6 · Calendario mensual de obra y deuda | Alta (bloquea casos reales) |
| 7 | T7 · Uso mixto con comercial en lease-up | Alta (bloquea el 1101) |
| 8 | T8 · Builder's risk como partida propia | Media |
| 9 | T9 · Caso dorado y tie-out en Excel | Alta |
| 10 | T10 · Arnés de backtest | Alta |
| 11 | T11 · Medición de falsos verdes con documentos reales | Alta |
| 12 | T12 · Prueba del enchufe de criterios | Alta |
| 13 | T13 · Registro de roles | Media |
| 14 | T14 · Expediente en tres piezas y limpieza editorial | Media |

---

## T1 · TIR y fecha de recupero en la caja resumida

**Problema:** la tabla resumen del ejemplo vigente (sección 15 del D272) muestra el múltiplo pero no la TIR, que es la métrica más relevante para decidir. Recalculada desde los flujos publicados, la Base da alrededor de 15,2% con refi y 14,4% sin refi, justo alrededor de la referencia histórica de 15%.

**Cambios:**
- Agregar a `results.json` y al resumen, por ruta (Base o Downside, con o sin refi): `irr_annual` (intervalo certificado D270 o PENDING), `payback_date` (primera fecha en que los cobros acumulados ≥ los aportes acumulados; si no ocurre, `null` con el motivo «capital no recuperado en el horizonte») y `peak_equity` (aporte acumulado máximo neto de cobros).
- Si la TIR no está certificada: mostrar «PENDING · raíz no probada», nunca una aproximación.

**Aceptación:**
- En el fixture D269/D270 la TIR aparece en las cuatro rutas, con el intervalo de la prueba de unicidad.
- `payback_date` se verifica de forma independiente sumando los eventos.
- Un caso con raíces múltiples sigue en PENDING.

---

## T2 · Distancia a la quiebra (fronteras matemáticas)

**Objetivo:** responder «cuánto puede empeorar cada variable antes de que el deal se rompa», sin usar umbrales de inversión.

**Drivers** (movimiento adverso desde Base y desde Downside):

| Driver | Celdas | Unidad del movimiento |
|---|---|---|
| Renta residencial | C8–C11 | % relativo |
| Cap de salida | C67 | puntos básicos |
| Sobrecosto de obra (hard) | costo vertical M3 | % relativo |
| Tasa de interés (obra y permanente) | C51–C53, C69 | puntos básicos |
| Retraso de lease-up | calendario M4 | meses |
| Vacancia y pérdida | C14 | puntos porcentuales |

**Fronteras** (todas matemáticas, ver regla 0.5):
- **F1 · Pérdida de capital:** múltiplo sobre todos los aportes = 1,00x.
- **F2 · Cobertura del servicio:** DSCR del permanente = 1,00x en el primer año completo.
- **F3 · Refi insuficiente:** la capacidad de refi (mínimo de LTV, DSCR y debt yield del term sheet) es menor que el saldo de obra más los costos de cierre.
- **F4 · Aporte adicional:** el primer movimiento que exige equity adicional por encima del caso original (informativa).

**Método:**
- Bisección sobre el driver con recálculo completo del motor; cada punto pasa por B12 y B16.
- Sonda de monotonía en m* ± ε. Si no es monótona, se reporta un intervalo o PENDING, nunca un punto elegido.
- El rango de búsqueda se declara en la configuración. Si no se alcanza la frontera, el resultado es «> límite de búsqueda», no 0 ni infinito.
- Una corrida bloqueada por evidencia deja PENDING esa celda.

**Salida:** `breakeven_matrix` en `results.json` (driver × frontera × escenario), con el valor, la unidad, el rango buscado, la monotonía verificada y la referencia del expediente de cada corrida.

**Aceptación:**
- El verificador independiente reproduce cada frontera con una tolerancia declarada.
- Una prueba con un driver no monótono sintético da PENDING.
- Una prueba con evidencia faltante da PENDING.
- Los ceros explícitos se respetan.

---

## T3 · Grilla de precio y precio máximo con metas configurables

**Objetivo:** que la hoja muestre cómo cambia el retorno con el precio del terreno sin depender del RLV oficial.

**Cambios:**
- Grilla de precio del terreno (por ejemplo −20% a +20% en pasos configurables) × {TIR, múltiplo, YoC, equity/TDC}, en Base y Downside. Deuda fija y ΔTDC = ΔP × (1 + C33), según lo acordado en SRC-03.
- `max_price_for_targets`: el precio máximo que cumple **metas que define el usuario en la configuración** (por ejemplo TIR ≥ x, múltiplo ≥ y). Rotularlo «precio para metas del usuario», no RLV.
- Slot `house_rlv` = PENDING («criterio por confirmar»), que se llena sólo con el archivo de criterios aprobado.
- Si el precio sale negativo, se conserva con bandera. Si no hay precio alcanzable, PENDING.

**Aceptación:**
- Prueba de monotonía.
- El verificador recalcula dos puntos de la grilla desde las celdas.
- `house_rlv` nunca se completa sin un criterio adoptado.

---

## T4 · Tornado de sensibilidades

**Cambios:**
- Reusar el programa D268 (15 drivers). Para los 6 drivers de T2 con un shock simétrico declarado en la configuración (no son defaults históricos), calcular ΔTIR y Δmúltiplo, y ordenar de mayor a menor impacto.
- Salida `tornado` en `results.json`. Las corridas sin caja quedan como NOT_EXECUTED o PENDING, visibles.

**Aceptación:**
- El orden es reproducible.
- Los empates comparten posición.
- Las corridas bloqueadas no desaparecen del gráfico.

---

## T5 · Hoja de decisión de una página (nuevo renderer B15, esquema v36)

**Formato:** Letter, una página, en español, generada sólo desde `results.json` reproducido por B16. El renderer anterior queda intacto para los perfiles anteriores.

**Bloques en este orden:**
1. **Encabezado:**
   - Proyecto, dirección, unidades por tipo, GSF/NRSF y área comercial.
   - Fecha de corte, revisión y huella abreviada.
   - Ruta (PRELIMINAR o integrada).
   - **Cobertura de datos**: «n de 55 campos respaldados · m supuestos · k PENDING».
2. **Caja por USD 10:** aportes iniciales y adicionales, cobros, sin recuperar, múltiplo, TIR (T1) y fecha de recupero. Base y Downside, con y sin refi, en 4 columnas.
3. **Métricas clave:**
   - Filas: YoC (NOI_uw), spread contra cap (base compatible), DSCR, debt yield, LTC, LTV, ocupación de equilibrio (económica; la física PENDING si C14 no tiene desglose), equity/TDC, CoC posrefi y equity recuperado en refi.
   - Columnas: **Base · Downside · Referencia · Estado**.
   - Sin criterios adoptados, **Referencia** muestra la tabla histórica en gris con la leyenda «referencia histórica, no vigente» y **Estado** dice «criterio por confirmar».
4. **Distancia a la quiebra (T2):** matriz compacta de drivers × F1–F3, en Base y Downside.
5. **Precio (T3):** una mini-grilla de 5 puntos y el precio para las metas del usuario. «RLV de la casa: criterio por confirmar».
6. **Tornado (T4):** los 6 drivers sobre la TIR.
7. **Fuentes y usos:**
   - TDC total, por unidad y por SF.
   - Deuda de obra, permanente y equity.
   - Barra de calendario: compra, obra, TCO, estabilización, refi y venta.
8. **Banderas:** discrepancias abiertas, supuestos sin respaldo y campos PENDING, cada uno con su responsable (del registro T13).
9. **Pie:** revisión, fuentes y la leyenda «No es un dictamen de inversión».

**Reglas de presentación:**
- Nunca mostrar «PASS» ni «FAIL» hacia afuera. Usar «cumple criterios», «no cumple criterios», «criterio por confirmar» y «PENDING · motivo».
- Ninguna celda vacía se muestra como 0.
- Las cifras se redondean sólo en la presentación.

**Aceptación:**
- Una sola página con el caso dorado (T9) y con el fixture D269.
- Prueba de desborde con nombres largos y 4 rutas.
- B16 coteja cada cifra del PDF contra `results.json`.
- Una revisión anterior queda bloqueada.

---

## T6 · Calendario mensual de obra y deuda (esquema v36-monthly)

**Problema:** el horizonte D266/D267 acepta sólo calendarios trimestrales y los préstamos de obra reales desembolsan e intereses devengan por mes.

**Cambios:**
- Grilla mensual para M4 (calendario), M5 (desembolsos, intereses y saldo), equity y caja. La operación estabilizada puede seguir siendo trimestral, con un puente declarado.
- Tasa mensual = convención declarada en el term sheet (por ejemplo actual/360 o 30/360). Sin convención declarada, PENDING.
- TIR con flujos mensuales: extender el certificado D270 a la grilla mensual (z^12) con la misma prueba de unicidad.

**Aceptación:**
- **Prueba de equivalencia:** un caso cuyos eventos caen sólo en fin de trimestre reproduce exactamente la caja del perfil trimestral.
- Prueba de un desembolso a mitad de trimestre.
- Prueba de cierre de obra que cruza el 1 de enero (§192.042).
- Los perfiles trimestrales anteriores siguen idénticos byte por byte.

---

## T7 · Uso mixto con comercial en lease-up (esquema v37)

**Problema:** el perfil actual rechaza el comercial parcialmente estabilizado, y el 1101 tiene alrededor de 34.228–35.493 ft² comerciales (discrepancia abierta de 1.265 ft²).

**Cambios:**
- Módulo comercial separado dentro de M2: área por local, renta base por ft², escalones, free rent, TI/LC, comisiones, NNN y recuperaciones, vacancia comercial y calendario de lease-up propio.
- NOI dividido en residencial y comercial. El sizing del banco y la valoración aplican la base que el term sheet declare. Si falta, PENDING.
- Cap de valoración y de salida por uso cuando la evidencia lo provea. Si no, se declara un cap combinado con su fuente.
- TI/LC entran en el presupuesto M3 o en el capex según el calendario.

**Aceptación:**
- Un caso sintético sólo residencial reproduce idéntico al perfil anterior.
- Un caso mixto con el verificador independiente.
- Un área comercial con discrepancia entre planos bloquea los dependientes, como hoy.

---

## T8 · Builder's risk como partida propia

**Cambios:**
- En M3: `builders_risk` como partida explícita (base, tasa o prima, plazo, fuente), separada del soft cost porcentual y del seguro operativo de M2.
- Evitar el doble conteo: si la cotización del GC lo incluye, se declara y no se suma.
- Sin dato, PENDING. Nunca va escondido dentro del soft %.

**Aceptación:**
- Prueba de doble conteo.
- Prueba de ausencia (PENDING).
- El TDC reconcilia con fuentes = usos.

---

## T9 · Caso dorado y tie-out en Excel

**Cambios:**
- Fijar **un** caso sintético de referencia, `golden_case_v1`, que se corre en cada versión y no cambia entre cortes. Cada cambio de resultado tiene que explicarse en la constancia.
- Generar `golden_case_tieout.xlsx` con **fórmulas vivas** (no valores pegados), construido desde las celdas fuente y no desde el motor: programa, NOI, TDC, deuda, refi, venta, caja trimestral o mensual, múltiplo y TIR (función IRR o XIRR de Excel).
- Recalcular con LibreOffice y comparar con `results.json` dentro de una tolerancia declarada (por ejemplo USD 0,01 por USD 10 y 1 pb de TIR).

**Aceptación:**
- El tie-out cierra.
- Una alteración inyectada en una celda fuente hace fallar la comparación.

---

## T10 · Arnés de backtest con proyectos cerrados

**Cambios:**
- La plantilla `backtest_case_template.xlsx` tiene, por proyecto, los inputs tal como se conocían al momento de decidir y los resultados reales (costo final, fechas, rentas logradas, refi, venta y caja real del equity).
- El comando `backtest run` corre el Mini-UW con los inputs originales y produce un reporte de diferencias por categoría: fuente, plazo, costo, NOI, servicio de deuda, venta y aportes o cobros.
- Métricas de error: diferencia de TIR, de múltiplo y de TDC y desvío del calendario.

**Aceptación:**
- Un proyecto sintético con «real» conocido.
- El reporte explica el 100% de la diferencia en categorías, con «no explicada» visible si queda resto.
- Los datos reales los carga el equipo; Codex no inventa ninguno.

---

## T11 · Medición de falsos verdes con documentos reales

**Cambios:**
- `false_green_study`: definición de la muestra (documentos, datos críticos), una plantilla de referencia independiente que llena una persona y el cálculo de la tasa = falsos verdes ÷ datos críticos, con su intervalo de confianza (Wilson o Clopper-Pearson).
- Reporte por tipo de documento (plano, cotización GC, term sheet, fiscal) y por bot.
- Meta declarada: 0 falsos verdes. El reporte muestra el tamaño de muestra necesario para afirmar una tasa máxima con un 95% de confianza.

**Aceptación:**
- Prueba sintética con falsos verdes inyectados que el estudio detecta.
- Ningún dato verde sin cita entra al conteo como correcto.

---

## T12 · Prueba del enchufe de criterios

**Objetivo:** demostrar que cargar los criterios de Lorena no cambia ningún número.

**Cambios:**
- Dos archivos de criterios **ficticios y opuestos**, `criteria_fixture_strict.json` y `criteria_fixture_lenient.json`, rotulados `synthetic_plug_test_only`.
- Una prueba que corre el caso dorado con: sin criterios, el estricto y el permisivo.

**Aceptación:**
- Entre las tres corridas, **todas las cifras** de `results.json` (caja, métricas, fronteras, grilla y tornado) son idénticas byte por byte. Sólo cambian los campos de estado y la columna Estado de la hoja.
- `house_rlv` se calcula sólo cuando el archivo trae una definición de RLV y queda PENDING en la corrida sin criterios.
- El loader de criterios valida operador, unidad, base de NOI, escenario y vigencia. YoC y spread no pueden ser vinculantes a la vez para el RLV.

---

## T13 · Registro de roles

**Cambios:**
- `roles_registry.json` con un esquema y campos **vacíos**: custodio de evidencia oficial, responsable de criterios, revisor financiero y aprobador autorizado. Cada rol lleva nombre, alcance, vigencia y fecha de designación.
- La hoja (T5) y las banderas usan este registro. Si un rol está vacío, se muestra «responsable por designar» y el dictamen formal queda bloqueado, como hoy.

**Aceptación:** prueba con un registro vacío y con un registro completo ficticio de prueba.

---

## T14 · Expediente en tres piezas y limpieza editorial

**Cambios:**
1. Generar tres salidas en lugar de un único PDF de 143 páginas:
   - **Resumen para el responsable de criterios** (≤ 8 páginas): las secciones 2–4 actuales, la caja anualizada, la hoja T5 de ejemplo y los pendientes.
   - **Expediente técnico** (alrededor de 40 páginas): flujo, Dots y bots, módulos, catálogo de fórmulas vigente y evidencia de pruebas.
   - **Anexo electrónico**: contratos históricos, índice de hashes, ledger completo de eventos y código.
2. El ledger de caja en el PDF va **anualizado** y sin filas en cero. El detalle completo, incluidos los ceros explícitos, queda en el JSON y el anexo.
3. El párrafo «Procedencia del catálogo: D250…» va una sola vez.
4. Títulos de las secciones D25x según su contenido (no «Si invierto USD 10…» repetido) y sin duplicados («D260 · D260», «D267 · D267», etc.).
5. Sección de pendientes en español: mapear los estados técnicos (`implemented_and_validated_for_…`, `await_real_case_…`) a frases de negocio. TEC-04 en español.
6. Una línea que reconcilie los hashes: el commit documentado frente al commit probado, y que la diferencia es sólo de documentación (o lo que corresponda).
7. Glosario externo: «cumple criterios / no cumple criterios / criterio por confirmar» en lugar de PASS/FAIL.

**Aceptación:**
- Conteo de páginas por pieza.
- Una prueba de que no queda ningún estado en snake_case en el texto visible.
- Una prueba de que no hay títulos duplicados.
- El manifiesto lista las tres piezas con su huella.

---

## Puerta «Listo para traer los criterios de Lorena»

Se considera listo cuando se cumple **todo** esto:

- [ ] T1–T14 implementadas con la batería completa en verde y constancia.
- [ ] La hoja de una página (T5) sale con el caso dorado y con un caso real en modo PRELIMINAR.
- [ ] El tie-out en Excel del caso dorado cierra (T9).
- [ ] Backtest con 3–5 proyectos cerrados, cada diferencia explicada (T10).
- [ ] Tasa de falsos verdes medida con documentos reales y su intervalo (T11).
- [ ] La prueba del enchufe de criterios pasa (T12).
- [ ] El registro de roles está completo, llenado por el equipo (T13).

**Después de la puerta**, lo único que se pide al responsable de criterios es completar `'Criterios PASS FAIL'!E7:H16` y responder L01–L07 en una sola reunión, con la planilla ya armada.

## Qué NO hace este bloque

- No adopta umbrales ni el RLV de la casa, y no resuelve L01–L07.
- No corre un dictamen real del 1101 ni de otro proyecto.
- No calcula retorno personal sin términos de reparto documentados.
- No despliega nada ni toma decisiones de inversión.
