# T109: fuentes vigentes declaradas y una página del recorrido liquidado

Una entrada local contiene el caso sintético T108, su registro completo de evidencia T46 y un UTC explícito. Si una fuente requerida o el cálculo falla, se retiran las cifras actuales y la página muestra pendientes. El registro no autentica contratos, revisión profesional o datos reales; decisión PENDING.

Desde la raíz del repositorio con Python y `requirements-reference.txt`:

```sh
PYTHONDONTWRITEBYTECODE=1 python tools/current_settled_miniuw_v1.py run \
  templates/current-settled-current-T109.json \
  --output /tmp/miniuw-T109-salida
PYTHONDONTWRITEBYTECODE=1 python tools/current_settled_miniuw_v1.py audit /tmp/miniuw-T109-salida
PYTHONDONTWRITEBYTECODE=1 python tools/check_current_settled_T109.py
```

El paquete tiene seis archivos: entrada, resultados, un PDF de una página, manifiesto de spans/cifras/agrupaciones, comprobación técnica y manifiesto de archivos. [Página sintética con evidencia declarada actual](review/miniuw-v1-current-settled-current-example/MiniUW_Resumen.pdf). [Página con evidencia vencida](review/miniuw-v1-current-settled-expired-example/MiniUW_Resumen.pdf). Cada ejecución produce un solo PDF; son casos internos de prueba, sin entrega o autorización financiera externa.

Se comprueban35 fuentes en este ejemplo: todas las fuentes de compra/obra, deuda, operación, saldo contable, pago y venta, eventos del inversor, catálogo vacío y definiciones/versiones requeridas. Cambiar un padre no renueva un hijo. Inicio de vigencia inclusivo, final exclusivo; sin TTL o reloj automático. Una revisión pendiente, estimación, sustitución, hash/localizador/contexto incompatible o evidencia faltante/duplicada bloquea.

La página muestra aportes1400, cobros840 y neto−560, con EM0,6 del perfil directo T77/T108; ingresos operativos60/90, sin sustituir la renta faseada T83/T95. Base de todos los aportes1400: por10, cobros6/neto−4. Es una escala del proyecto, sin términos LP/JV personales. Incluye fechas/rangos, cantidad de eventos/ceros, liquidación del seguro, caja anual bruta/neta, TIR por intervalo exterior, riesgos y capital/CoC pendientes cuando faltan bases.

Los diez criterios quedan pendientes y sin umbral, incluso con proyecciones de caja/EM/TIR conocidas. El adaptador de la hoja original de55 campos para esta ruta,54 mapeos globales, autoridad real, capital/CoC/retorno personal y aceptación financiera siguen abiertos. No se adopta una hipótesis, renueva evidencia o aprueba Full UW automáticamente.

Una página, hasta256 eventos agrupados y doce años completos; el calendario individual y todas las raíces/motivos permanecen en JSON. Se rechaza desborde o texto no representable en vez de cortar, omitir o crear otra página. Validación determinista con pypdf de una página y extracción de cada span; no es auditoría financiera independiente o certificación visual externa. Recuperación completa desde fuentes/versiones, reintento idéntico y rechazo de otro resultado. [Definición T109](technical-implementation-T109.md).
