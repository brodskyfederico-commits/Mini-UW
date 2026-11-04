# Mini-UW v1 con renovaciones de seguros

La entrada combina el expediente T91 completo con libros de todas sus filas de seguro. Cada libro declara pólizas sucesivas, primas, asignaciones por período y cuotas agrupadas. El [contrato](technical-implementation-T93-T95.md) exige conciliación con los costos/pagos ya suministrados y con todas las fuentes al mismo UTC antes de mostrar el retorno.

| Entrada | Contenido |
|---|---|
| `schema` | `miniuw.synthetic-v1-policy-renewal-case.v1` |
| `scheduled_case_utf8` | Bytes UTF-8 exactos del expediente con seguros/impuestos T91 |
| `policy_books_utf8` | Un libro completo por cada concepto de seguro, con fuentes y hash del calendario agregado T90 |
| `registry_utf8` | Registro de evidencia de todas las fuentes; 43 vínculos en el ejemplo |
| `as_of_UTC` | Mismo instante UTC explícito que el expediente padre |

El libro usa `miniuw.synthetic-insurance-renewal-book.v1`. Cada póliza tiene fechas sucesivas, prima y fracciones suministradas por intersección exacta con los períodos operativos. Cada prima se asigna completamente; las cuotas se agrupan expresamente hacia las obligaciones agregadas con igual fecha e importe. Una cuota puede vencer después de terminar esa póliza, dentro de la ventana operativa declarada. Esto no autentica condiciones contractuales o cobertura legal. El perfil exige liquidación íntegra dentro de tenencia; pólizas simultáneas, reembolsos y obligaciones fuera de ventana siguen pendientes.

Desde la raíz del repositorio, con Python3.11 o posterior y dependencias de `requirements-reference.txt` instaladas:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python tools/renewal_miniuw_v1.py run templates/miniuw-v1-policy-renewal-case.json --output /tmp/miniuw-policy-demo
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python tools/renewal_miniuw_v1.py audit /tmp/miniuw-policy-demo
```

La carpeta contiene ocho archivos: `case.json`, `results.json`, `execution-evidence.json`, `MiniUW_v1_Resumen.pdf`, `report-manifest.json`, `audit.json`, `schedule-review.txt` y `package.json`. El PDF tiene una página; los libros, grupos, fuentes y bloqueos completos permanecen en los registros internos. Usar una carpeta nueva por revisión; un reintento idéntico verifica bytes, una salida diferente/incompleta se rechaza.

Una corrida válida pero bloqueada genera un informe PENDIENTE con código0; consultar `policy_blockers` y `blockers`. JSON/perfiles no admitidos, datos fuera de límites o página no representable devuelven código2. La recuperación y audit reconstruyen todas las fuentes y resultados; actualizar hashes de un resultado manipulado no evita esa comprobación.

La [demostración](review/miniuw-v1-policy-renewal-example/package.json) mantiene primas10/10, gastos10/10 y pago agregado5/15, con cobros778 sobre aportes1.400. La [renovación sintética12](../templates/miniuw-v1-policy-renewal-twelve-case.json) suministra prima total22, gasto10/12, pagos5/17 y nuevas fuentes compatibles: cobros776 y resultado−624. Las fracciones agregadas5/11 y6/11 están suministradas en esa revisión. No se pronostica una prima de mercado ni se ajustan variables automáticamente.

Si cambia o vence un libro, una fuente del padre o una fecha/importe/grupo, se retiran las cifras actuales afectadas del proyecto, métricas y calendarios. Se conservan los originales y hashes para revisión. Suficiencia de cobertura, autoridad real, reglas contables/fiscales, asignación personal y validación financiera siguen pendientes. Sin despliegue ni decisiones reales.
