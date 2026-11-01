# M1 — Entradas, programa, evidencia y normalización

Estado: ocho contratos candidatos. Se preservan las 55 definiciones originales del Input Sheet, sin inventar nuevos valores ni declarar suficientes esos campos para toda la economía/calendario. No hay paquete de planos/deal real ni dos lectores independientes validados.

| ID | Contrato | Fuente / alcance |
|---|---|---|
| M1-01 | Recepción y procedencia | Master §1; Manual p.16/p.38. Conservar original/hash, nombre, versión declarada, tipo, páginas y ubicación; extracción no prueba autenticidad. |
| M1-02 | Programa y grupos de unidades | Master §2; Manual p.7. Conteos explícitos por unit type/dormitorio, mercado/asequible; reconciliar totales sin contar etiquetas. |
| M1-03 | Áreas y unidades físicas | Master §3 Areas; Manual p.7. GSF, NRSF, áreas unitarias/comerciales, parking y sitio separados; no usar ratios de eficiencia inventados. |
| M1-04 | Input Sheet original | Inputs A/B/C/D/E/F, 55 filas. Literal, valor normalizado, unidad/base, obligatoriedad, nota y fuente preservados. Rangos y semántica pendientes donde no aprobados. |
| M1-05 | Estados y aplicabilidad | Manual p.15; traspaso §3. Cero explícito, faltante, inválido, conflicto y no aplicable justificado distintos; sin default financiero. |
| M1-06 | Lecturas y conciliación | Manual pp.38–39; traspaso §7. Citas y afirmaciones alternativas, correcciones enlazadas; coincidencia no demuestra independencia de lectores ni verdad. |
| M1-07 | Normalización y consumidores | Manual pp.7–14; traspaso §§3/5. Contrato por campo con tipo/currency/unit/período/base y módulos; no asumir moneda o formato porcentual de un símbolo. |
| M1-08 | Cierre de paquete y revisiones | C1; traspaso §§6–7. Mapear dependencias/faltantes por alcance; cada revisión invalida descendientes y preserva historia sin mezclar runs. |

## Clasificación y límites de normalización

El tipo declarado y las unidades originales se conservan antes de transformación. Los campos monetarios mantienen moneda sin completar si no se aporta; el símbolo $ no es autenticación de moneda. Los ratios no se convierten por escala supuesta: un 5 y un 5% no son equivalentes sin formato aprobado. Períodos de tasa, duración entera/fraccionaria y fecha de flujo se dejan explícitos/pending.

Texto numérico, TBD, fórmulas de workbook y celdas vacías requieren estado propio. No ejecutar fórmulas/macros por recibir el archivo; registrar fórmula, valor cacheado si existe y estado de confiabilidad, sin tratar caché como cálculo propio. Las alternativas C80:C82 son solicitudes de escenarios, no instrucciones ejecutables del documento.

Las condiciones originales REQUIRED/IF APPLIES/OPTIONAL se conservan; no se eliminan métricas para evitar bloqueos. Si un tipo de unidad o uso no existe, la aplicabilidad necesita evidencia. El valor cero de un campo no prueba ausencia del uso. La condición de C36 según GSF/costo no cambia el alcance de otros datos de programa.

El mapa enriquecido queda en `input-contract-map.json`. Sus propuestas de tipo y consumidor son diseño, no esquema aprobado ni validación de rangos. No cambia el workbook original ni completa C/F. Los rangos expertos, moneda y calendarios reales permanecen sin valor cuando faltan.

Cierre pendiente: datos originales del deal, fuentes y reglas aplicables, independencia de lectura, resolución de conflictos, validación de formatos/rangos con aprobación y prueba integrada C1. El mapa documental no demuestra implementación de ese flujo.
