# Riesgo de caja de las hipótesis T105

Observa caja aún no recuperada, pico neto por fecha y dependencia del cobro de venta para cada participante ficticio T104. No define capital contable, liquidez disponible, pérdida económica final o un riesgo financiero completo. El retorno personal real y la decisión siguen PENDING.

Desde la raíz del repositorio, Python y dependencias de `requirements-reference.txt`:

```sh
PYTHONDONTWRITEBYTECODE=1 python tools/participant_cash_risk_miniuw_v1.py run \
  docs/review/miniuw-v1-cash-participation-example/allocation-evidence.json \
  --output /tmp/miniuw-T105-riesgo
PYTHONDONTWRITEBYTECODE=1 python tools/participant_cash_risk_miniuw_v1.py audit /tmp/miniuw-T105-riesgo
PYTHONDONTWRITEBYTECODE=1 python tools/check_participant_cash_risk_T105.py
```

El paquete interno contiene tres JSON: evidencia T104 con sus bytes originales, riesgo y manifiesto. No vuelve a anidar la evidencia ni genera otro PDF externo. `docs/review/miniuw-v1-participant-cash-risk-example/` conserva el ejemplo. Al recuperar se repite T104 desde sus fuentes y después el observador; modificar cifras/hashes no valida una falsificación. Inventario exacto, reintento idéntico y otra salida en otro directorio. Uso local, sin publicación o despliegue.

En la hipótesis1/4, aportes350 y cobros194,50 dejan155,50 de caja no recuperada al corte. El pico neto al cierre y su cota superior son350; la venta aporta144,50 de194,50 cobros, razón289/389. Sin contar ese cobro, la brecha aritmética sería300. No recalcula un escenario sin venta ni dice que esos importes sean capital exigible, pérdida final o fondos disponibles.

Cuando aporte y cobro coinciden en fecha, conserva brutos y muestra cotas: cierre y posible máximo intradía, con orden real pendiente. No interpreta el orden de la lista como secuencia de pagos ni supone que un cobro pueda financiar otro aporte. Los puntos sin movimientos y eventos cero quedan visibles en el detalle.

Los importes y cotas se concilian con el proyecto sólo bajo el perfil de fracciones constantes T104. Los porcentajes no se suman. Fracción0 conserva caja/cotas0 con dependencia de venta indefinida si no cobra; un reparto pendiente deja todo el riesgo atribuido pendiente. Capital/equity/CoC, fondos y financiación auténticos, Downside y54 mapeos semánticos siguen abiertos. [Definición T105](technical-implementation-T105.md).
