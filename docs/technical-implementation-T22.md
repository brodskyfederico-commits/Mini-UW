# Integración de renta calculada con NOI y DSCR

T22 conecta la renta y gastos de T21 con el productor condicional de NOI T19. El contrato exige hashes de fuente y ejecución residencial, contexto común, un inventario adicional declarado completo, partidas de ingresos adicionales explícitas, impuesto comparable, coeficiente fiscal y supuestos del modelo NOI. No activa criterios de inversión ni adopta política fiscal.

Los ingresos adicionales pueden representar importes finales de otros ingresos o comercial aportados para el período; este bloque no los calcula ni les vuelve a aplicar vacancia. No se declara que su inventario esté acreditado por marcarlo completo. Un inventario adicional vacío bloquea la compilación: si el ensayo declara cero ingresos adicionales, debe aportar una partida cero explícita con procedencia y metadatos.

## Ensamblaje y procedencia

Primero se reproduce el productor residencial. Una fuente o ejecución distinta de la vinculada, un contexto diferente o un productor bloqueado impiden compilar. El caso NOI generado incorpora renta efectiva y cada gasto calculado con referencia al hash y ubicación exacta del productor. Las partidas adicionales y parámetros fiscales conservan sus referencias originales. No se reescriben valores para cumplir un criterio.

La fuente compilada se procesa con el contrato existente de NOI: unidades, moneda, período, base de devengo, fuentes, dominios y faltantes siguen controlados. Si falta k, el importe antes de impuesto puede estar calculado mientras NOI continúa pendiente. Una fuente compilada fuera del contrato o presupuesto de transporte del consumidor se conserva como evidencia bloqueada; no se fuerza su aceptación ni se oculta una partida.

`assemble_rental_noi` devuelve ejecución inmutable con productor residencial completo, fuente compilada y ejecución NOI cuando existen, enlaces y causas. `save_rental_noi` y `load_rental_noi` capturan y reproducen fuente residencial, especificación, productor y fuente compilada. Se verifican versiones de código y documentos; el fallo de captura revierte el paquete local completo. No hay cambio de esquema ni publicación financiera.

## Demostración de la cadena completa

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 tools/demo_residential_noi_chain.py
```

Con datos ficticios explícitos: diez unidades, renta mensual por unidad de 100, doce meses y pérdida de 10% producen renta potencial 12.000 y efectiva 10.800. Concesión cero expresamente declarada. Gastos de 5% de esa renta, 12 por unidad/año regular y 140 fijos producen 540 + 120 + 140 = 800.

Una partida adicional cero y el modelo fiscal condicional con F=100 y k=1/4 producen operación antes de impuesto 10.000, impuesto 2.000 y NOI 8.000. La cadena conecta este NOI con servicio anual equivalente calculado de 1.200 y obtiene DSCR 20/3x. No se aplica un mínimo bancario ni un umbral de inversión. La anualización del préstamo no extiende su vencimiento o acredita pagos/balloon.

La demostración reabre dos paquetes: ensamblaje residencial/NOI y puente NOI/deuda/DSCR. Reproduce ambos y comprueba que la fuente y ejecución NOI del primero coinciden exactamente con las consumidas por el segundo. No se afirma que el paquete DSCR por sí solo reproduzca la matemática residencial: esa evidencia está en el paquete de ensamblaje enlazado. Las dos capturas son transacciones separadas; un fallo posterior puede dejar un paquete previo sin su siguiente etapa, sin convertirlo en decisión completa. Las bases de prueba son temporales y no se conservan en Git.

13 pruebas nuevas cubren la cadena exacta, procedencia derivada, inventario adicional, versiones/contexto, productor falso, datos ausentes, parámetros fiscales, moneda/período, cero/ausencia, políticas no soportadas, guardas y recuperación completa, más el enlace de fuentes y ejecuciones entre ambos paquetes tras reapertura. Junto con las 16 de T21, suman 29 nuevas y 419 técnicas en total.

Permanecen pendientes el productor comercial, políticas/alcances reales, calendarios de lease-up y caja, asequibilidad, revisión profesional y aceptación financiera integrada. Los 36 casos originales de aceptación financiera y 56 casos de diseño D02/D03 no se dan por ejecutados ni cerrados. No hay evaluación real, despliegue o cierre de módulo.
