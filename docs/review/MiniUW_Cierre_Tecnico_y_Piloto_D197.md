# Mini-UW · Cierre técnico y preparación del piloto

Revisión del reporte D196, con evidencia al mismo corte. La devolución del especialista está en «MiniUW_Analisis_Reporte_D196.pdf», p. 1 para los hitos 13–15 y p. 2 para el hito 16 y el piloto. SHA-256 `31cd5011c4b07f1fe1e0a866928e016a7915b64feec439c53cc92e2764880ca0`.

| Indicador | Resultado | Cómo se cuenta |
| --- | --- | --- |
| Checklist técnico sintético v1 | **12 de 16 · 75 %** | Un punto por hito comprobado en su perfil. Hitos abiertos sin crédito. El conteo no estima esfuerzo ni plazo. |
| Preparación del piloto real | **0 de 6 · 0 % con cierre documentado** | Un punto por condición de piloto completamente acreditada en el expediente al corte. Se reconocen plantillas, definiciones candidatas y pruebas sintéticas como preparación parcial. |

El alcance residencial del Mini-UW v1 sigue según [D189](../preliminary-pilot-readiness-D189.md). El piloto real sigue PENDING. El PDF interno acompaña este plan. [Reporte corregido](MiniUW_Reporte_Procesos_y_Avance_D196_Corregido.pdf).

## Pruebas de cierre técnico

| Hito | Prueba y resultado exigido | Evidencia al corte y pendiente |
| --- | --- | --- |
| **13 · Ingreso desde planillas y respaldos** | Armar un expediente sintético nuevo sin editar JSON. Alterar una celda de una planilla ya registrada y usar la revisión anterior. B04 o la verificación de huella debe bloquear el insumo e identificar archivo y celda cuando corresponda. Repetir el armado con exactamente los mismos archivos, versión y parámetros. Los archivos e identificadores derivados deben reproducir sus huellas. | D171 prueba blancos y ceros. D194 verifica la identidad de los criterios. Falta el armado repetible desde los archivos de entrada con ambas sondas en el mismo flujo. |
| **14 · Calendarios y rutas** | Ensayar refi con un tramo de solo intereses y transición a amortización, venta sin refi por el mismo ingreso y obra que cruza el 1 de enero. Cotejar intereses, principal, caja y fechas por escenario. Para el corte fiscal usar mejoras utilizables antes, al y después del 1 de enero, más un caso con evidencia incompleta. Aislar la mejora del terreno y de las partes ya utilizables. Usar importes y supuestos fiscales declarados para la prueba sintética. | D194 está comprobado con calendario trimestral y venta después de la primera cuota permanente. D102 prueba la ruta sin refi en su perfil. Falta validarlas desde el mismo ingreso y cotejar el efecto fiscal anual del calendario. |
| **15 · Criterios, NOI y RLV** | Quitar un PASS o FAIL requerido por una frontera del RLV y verificar PENDING. Restituirlo en una revisión nueva y verificar el recálculo. Probar una regla sin FAIL fuera de las dependencias del RLV. Exigir exactamente un criterio de rendimiento vinculante para la grilla, YoC o spread. Rechazar ambos vinculantes. Pedir base de NOI y ventana para cada criterio que dependa de NOI, cotejar con el productor y bloquear la métrica ante incompatibilidad. | D193 ya elige YoC o spread para la grilla y D196 prueba faltantes en equity/TDC y TIR. Falta cerrar el contrato de entrada y probar los casos cruzados. Las métricas de YoC y spread pueden seguir visibles y atender su política de screening separada. |
| **16 · Aceptación desde una copia limpia** | Ejecutar expedientes completo, adverso, incompleto y corregido en el VPS. Verificar fuentes = usos por período con caja inicial, final y restringida identificadas. En el ensayo LP/GP conciliado, verificar LP + GP = caja distribuible en cada fecha. Probar que P* y su vecino inferior cumplen y que su vecino superior deja de cumplir todos los PASS. Verificar por separado que el vecino superior al último precio antes de FAIL cruce al menos un FAIL. Si faltan puntos vecinos, dejar la frontera PENDING. Con C14 combinado, la ocupación física debe quedar PENDING con motivo. | D179, D170 y D184/D193 cubren invariantes en ensayos de referencia. Falta la aceptación conjunta, reproducible y registrada sobre la misma versión. |

Para el hito 15, las métricas sin dependencia de NOI declaran su propia base, por ejemplo flujos fechados para TIR y múltiplo. YoC usa NOI de underwriting después de reservas. Spread coteja la misma base que el cap comparable y registra su ventana. DSCR y debt yield usan NOI bancario. Las valoraciones de refi y venta usan la base que respalda su cap. [Bases e invariantes ensayados en D184](../workbook-performance-policy-D184.md) · [Criterios Downside D196](../workbook-downside-pass-only-D196.md).

## Checklist del piloto real

| Condición | Evidencia necesaria para cerrar | Estado al corte |
| --- | --- | --- |
| Responsables designados | Custodio de evidencia oficial, responsable de criterios y revisor financiero con función y autoridad registradas. | PENDING · Designaciones |
| Definiciones y criterios vigentes | Aprobación de SRC-02 y SRC-03, criterios Base/Downside, aplicabilidad y versión trazable. Lorena completa el Excel de criterios. | PENDING · Aprobación |
| Documentos reales cotejados | Expediente autorizado con Base/Downside y respaldos del equipo del proyecto. Comparar extracción con una lectura independiente, registrar fallos, denominador y alcance. Meta del especialista de cero falsos verdes observados en la muestra documentada. | PENDING · Validación real |
| Prueba retrospectiva | 3–5 proyectos cerrados, comparación con resultados reales y explicación de cada diferencia relevante. | PENDING · Muestra y cotejo |
| Corridas en paralelo | Primeros 2–3 casos contra el proceso actual, reconciliación de las diferencias y revisión registrada. | PENDING · Corridas reales |
| Florida, módulo M2 | Documentar aplicabilidad, año fiscal, clasificación, valores tasables y tasas por componente escolar y no escolar. Verificar el estado de terminación al corte y el efecto de mejoras y cambios de titularidad según corresponda. | PENDING · Implementación y validación por caso |

### Alcance fiscal y presentación

Florida §192.042 contempla la tasación al 1 de enero y excluye de la valoración las mejoras o partes aún no sustancialmente terminadas en esa fecha. La condición se vincula con la posibilidad de usar la mejora o una unidad autosuficiente para su finalidad. El boletín estatal PTO 26-21 informa que la Enmienda 3 aplica desde el padrón fiscal 2027. El 5 % limita, cuando aplica, el crecimiento anual de determinada valoración tasada no escolar. El módulo fiscal todavía requiere contrastar la normativa de implementación y la evidencia del predio. [Florida §192.042(1)](https://www.flsenate.gov/Laws/Statutes/2026/192.042) · [Texto aprobado, art. VII §4(g)–(h), pp. 6–7](https://www.flsenate.gov/Session/Bill/2026F/1F/BillText/er/PDF) · [Florida DOR, PTO 26-21](https://floridarevenue.com/property/Documents/PTO_BUL_26-21.pdf).

Para la presentación profesional se deja registrada la sugerencia de mostrar **«Cumple criterios»** en materiales para clientes. Se retomará en esa etapa.
