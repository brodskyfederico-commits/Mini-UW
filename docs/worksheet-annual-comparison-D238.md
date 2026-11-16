# Si invierto USD 10, ¿cuánto cobro y cuándo?

[Comparación anual de una página](review/MiniUW_D238_Comparacion_Anual_USD10.pdf). El PDF reúne las cuatro rutas de D237 sobre USD 10 de equity inicial agregado del proyecto. Dentro de Base y Downside se usan la misma obra, el mismo NOI trimestral y la misma fecha, precio y costos de venta. El ensayo mide las diferencias de caja por estructura de deuda. El dictamen real del 1101 y su retorno histórico siguen PENDING.

Cada fila fechada separa un aporte y un cobro por ruta. En una misma fecha se conservan como filas distintas los aportes de obra, refinanciación, operación y venta. El resumen distingue aporte inicial, aportes adicionales, cobros por fuente y saldo sin recuperar. Los totales se redondean al final.

## Reproducir el PDF

    PYTHONPATH=src:tools python3 tools/miniuw_worksheet_v1.py compare-annual expediente \
      --current-revision vigente.json --with-refi annual_hold_with_refinance \
      --without-refi annual_hold_without_refinance --output MiniUW_Comparacion_Anual.pdf

Conservá el recibo JSON de la salida estándar. Incluye las huellas del PDF, los resultados auditados, la revisión y las cuatro cajas exactas. La exportación se bloquea si falta una ruta, sus bases de comparación no concilian o la revisión cambia al publicar. La prueba test_worksheet_annual_comparison coteja los 52 movimientos de las cuatro rutas, los totales y el bloqueo por revisión.
