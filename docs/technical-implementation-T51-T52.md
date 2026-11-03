# T51–T52 — recuperación de caja por tramos con mínimos y topes

Extiende el perfil sintético T48–T50 dentro de M7. No adopta contratos, comisiones, leyes, escenarios o criterios de inversión. Recuperación de caja al corte, pérdida económica definitiva y retorno personal son conceptos distintos.

## T51: dominio y partición exacta

Se reproduce T49 completo desde NOI/valor/costos/límites y deuda/caja/capacidad/retorno. Una base bloqueada, impuesto sin resolver o conflicto no habilita el análisis. La entrada liga su hash y declara un dominio de precios cerrado, finito y no negativo que contenga el precio base. Requiere referencias explícitas para mantener otras fuentes fijas y asumir que el perfil de cargos aplica en todo ese dominio. Una valoración previa en el cierre restringe la evaluación al punto base hasta resolver su consistencia por separado.

Los quiebres provienen de las intersecciones exactas de cada cargo porcentual con sus mínimos/topes monetarios. Se conservan los extremos del dominio, se deduplican coincidencias y se incluyen todos los quiebres interiores. Cargos fijos o de tasa cero no generan divisiones por cero. El presupuesto técnico de segmentos debe suministrarse entre 1 y 129; si es insuficiente se bloquea sin una solución parcial. Un dominio puntual se evalúa como tal.

En cada tramo se identifica la fórmula activa de cada cargo, mínimo o máximo. Si C(P) es su suma, el resultado de caja agregado es G(P)=P−C(P)+K, con K=G(P0)−P0+C(P0) obtenido del cálculo base reproducido. La identidad sigue conservando distribución menos aporte cuando el residual cambia de signo; no presupone financiación del cash-in. Se comprueba que la fórmula del tramo coincide con el cálculo limitado en ambos extremos.

Se resuelve G(P)≥0 por tramo con aritmética racional exacta y se unen únicamente intervalos que se tocan o solapan. No se fuerza un único piso: puede haber varios intervalos separados, ninguno o todo el dominio. Se conservan también los puntos o intervalos completos donde G=0, incluidas zonas planas y raíces en quiebres. Ninguna variable del deal se cambia ni se genera un escenario en la frontera para obtener PASS.

La conversión a exit cap usa P=N/c para NOI forward fijo y c>0, invirtiendo cada componente del conjunto de precios y conservando inclusión/extremos abiertos no acotados. Precio cero con NOI positivo no implica un cap finito; con NOI cero, solo el precio cero es alcanzable bajo ese perfil. La equivalencia con EM≥1 se etiqueta únicamente si los aportes brutos ajenos al cash-in variable de esa venta son positivos.

## T52: vigencia de fuentes y del dominio

Se reproduce T51 y T46 exactamente al instante UTC suministrado. El inventario cubre los 22 bindings técnicos de T50 y la especificación adicional de dominio/hipótesis/presupuesto de T51: 23 en el ejemplo. Las otras fuentes vigentes no permiten omitir o usar una revisión anterior de ese dominio. Fuente/localizador/contexto distintos, vencimiento, estimación, sustitución o revisión pendiente dejan el nuevo resultado actual sin análisis expuesto; la historia permanece intacta.

Se conservan bloqueos del análisis y del cálculo bancario/costos original. Un conjunto de recuperación vacío es un resultado matemático válido bajo las hipótesis, no un FAIL de inversión. Un análisis calculable/vigente tampoco es PASS, revisión autenticada o aprobación. No hay reloj implícito, monitor o publicación financiera habilitada.

## Validación y límites

Pruebas independientes de cargos, quiebres, continuidad, signos de beneficio, raíces exactas y conjuntos separados/planos; invariancia del resultado al repetir la cadena desde otro precio; cero, empates, dominios puntuales/truncados y presupuesto; linaje/replay de fuentes/resultados y rechazo de falsificaciones con hash actualizado. Se verifica vigencia del nuevo binding y conservación del resultado histórico al vencer.

La extrapolación sobre el dominio es una hipótesis suministrada, no evidencia de contratos/tributación aplicables o validez del NOI/cap. No se recalculan calendario, financiación alternativa, construcción, impuestos no modelados o variables de mercado. Cada nuevo precio a usar como caso debe recorrer sus propios controles de funding/targets/fuentes. Sin retorno personal, pérdida económica final calculada, bundle SQLite runtime, despliegue o decisiones reales. Originales, criterios vacíos e implementaciones previas se preservan.
