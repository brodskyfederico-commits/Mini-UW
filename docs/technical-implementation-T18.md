# Vista interna sintética de una página

T18 genera un PDF interno acotado desde una ejecución T15 reproducida contra su DOCX y caso exactos. Muestra diez métricas, valores Base/Downside, PASS Base/Downside, FAIL Base, comparaciones y todos los bloqueos que quepan dentro del perfil. La cabecera mantiene ESTADO OPERATIVO PENDIENTE y distingue el resultado de simulación. Los datos son ficticios y los umbrales documentales no se adoptan como política activa.

La página es horizontal de 792 × 612 puntos, con fuentes monoespaciadas estándar del formato PDF. Se verifica el ancho de cada texto antes de emitir bytes. Valores porcentuales, bps y múltiplos se convierten exactamente; una fracción sin decimal finito se muestra como fracción. No se redondea para decidir. Identidades demasiado largas, caracteres que la fuente no pueda representar, controles, valores desbordados, bloqueos desconocidos o más de tres líneas de bloqueos impiden generar la vista. No se recorta ni omite contenido para forzar una página.

El perfil es una vista de scorecard para pruebas internas, no la salida externa final de un deal. No incluye todavía el relato de $10, historia completa de capital, key numbers, sensibilidad, precio soportado o riesgos con evidencia. La construcción de una página y su legibilidad no acreditan esas piezas ausentes, revisión profesional, accesibilidad general o publicación vigente. La futura salida externa conserva sus requisitos completos de M9.

El generador usa biblioteca estándar y no ejecuta fórmulas o contenido de una fuente. Los textos se escapan como literales PDF y se rechazan controles. El PDF no contiene acciones, enlaces, anotaciones ni adjuntos activos. El manifiesto conserva hashes del PDF, fuente, caso, ejecución y generador, valores y estados mostrados, y las causas exactas junto con su texto legible. Un hash acredita bytes, no aprobación.

Son 12 pruebas nuevas usando un lector PDF independiente ya incluido en las dependencias del paquete: una sola página, tamaño horizontal, contenido inactivo, diez métricas y bloqueos completos, PENDIENTE visible, alcance Base parcial, escalas exactas, frontera sin redondeo, escape de textos, caracteres no representables, desbordamientos, evidencia falsa o cruzada, manifiesto y determinismo. La vista entregada también se renderizó y revisó visualmente y se comprobaron los límites de sus textos.

## Demostración integrada T16 a T18

Desde la raíz del repositorio, con `requirements-reference.txt` instalado para los controles:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 tools/demo_integrated_synthetic_review.py --preview-output /tmp/MiniUW_vista_sintetica.pdf
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v
```

La demostración crea un original Base PENDIENTE con YoC ficticio de 6%, una propuesta explícita a 7% que simula PASS Base y un descendiente explícito a 5% que simula FAIL Base. Son observaciones ficticias suministradas, sin optimización automática. Reabre el archivo y la cola, verifica la cadena y conserva registro, sustitución y retirada. Las bases se crean en un directorio temporal y se eliminan al finalizar; no representan un respaldo runtime real.

El PDF usa otro fixture Base/Downside completo en valores ficticios, con un bloqueo de aplicabilidad de asking/RLV Downside. Su resultado conjunto permanece PENDIENTE. Ese documento y su manifiesto se conservan como ejemplo interno reproducible, sin envío a terceros.

T16, T17 y T18 suman 46 pruebas técnicas nuevas: 354 en total. Permanecen separados los 36 casos originales de aceptación financiera y los 56 casos de diseño D02/D03. No hay cierre de módulos financieros, aplicación real de criterios, revisión profesional autenticada, decisión real o despliegue.
