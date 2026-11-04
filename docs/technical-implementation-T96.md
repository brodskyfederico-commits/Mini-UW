# T96: caja anual y contexto en la página del inversor

El resultado T94 ya contiene aportes, cobros y caja neta por año calendario. La página anterior T95 mostraba sólo cobros operativos/CoC en esa sección. T96 presenta los valores existentes en la misma página: A = aportes brutos, C = cobros brutos, N = caja neta, O = cobros operativos y CoC condicional. Conserva años sin cobros, ceros y pendientes; no anualiza una ventana parcial ni agrega una fórmula financiera.

La línea de contexto incorpora la moneda, el alcance de equity agregado y la ventana de caja, con punteros explícitos en el manifiesto. Cada fila anual apunta a año, aportes, cobros, neto, cobro operativo, base y CoC dentro de `current_project_return_story`. La moneda/ventana actuales quedan pendientes si la puerta completa retira la proyección.

`render_investor_onepage(raw, run)` exige reproducir el resultado T94 desde sus bytes exactos, reutiliza la composición T95 guardada y recompone sus spans en una página con el mismo presupuesto geométrico. No admite resultados alterados aunque se recalculen sus hashes; los textos se codifican y verifican dentro de sus límites. El manifiesto identifica T96, su código/definición, la versión del renderer padre, el manifiesto padre, fuente y resultado.

El perfil de ejemplo tiene equity agregado aportado 1.400 y cobrado 778, resultado −622. La caja neta de la ventana es −1.400 en 2026 y +778 en 2027; cobros operativos 0 y 200, respectivamente. CoC permanece pendiente por falta de base anual. La ventana incluye un tramo operativo de 2027, sin certificar un año operativo completo. El caso alternativo de renovación12 cobra776 y conserva resultado−624.

Este componente cambia presentación y trazabilidad. No cambia fuentes, criterios, resultados, TIR, métricas, políticas, reparto ni decisiones. Los capitales remanente/retenido siguen pendientes; no se sustituyen por aportes no recuperados. Retorno personal, datos reales, autoridad, aceptación financiera y publicación productiva siguen pendientes. Ningún PASS o uso real habilitado.

La API nueva es un renderer callable. El CLI y paquete de ocho artefactos T95 conservan su versión anterior; no se modifican ni se declara una nueva recuperación portable del renderer T96. El ejemplo T96 incluye PDF, manifiesto, resultado T94 sin cambios y comprobación de página/textos, ligados al expediente T95 existente; esos cuatro archivos son evidencia interna, no un segundo PDF externo de un deal.

El contrato de salida D07 comprueba 23 campos, dos corridas actuales y una retirada, con 21 consistencias exactas por corrida actual y sus punteros de presentación. Las pruebas técnicas de T96 verifican anualidad/metadata, retiro, rechazo de resultados falsificados y presupuesto de página. No son auditoría financiera independiente. D04/D05/D06 y todos los productores anteriores permanecen intactos. Sin despliegue ni decisiones reales.
