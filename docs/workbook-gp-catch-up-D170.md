# Si invierto USD 10, ¿cuánto cobro y cuándo?

D170 · Simulación de catch-up del GP sobre D169 y los flujos de D166. Cada columna se normaliza por USD 10 iniciales propios del rol.

| Movimiento | Base LP | Base GP | Downside LP | Downside GP |
|---|---:|---:|---:|---:|
| Aporte inicial · 30/03/2027 | 10,00 | 10,00 | 10,00 | 10,00 |
| Aportes adicionales | 4,87 | 4,87 | 8,19 | 8,19 |
| Refi · Base 30/09/2028 · Downside 30/03/2029 | 2,85 | 2,85 | 2,45 | 2,45 |
| Operación · Base 30/12/2028 · Downside 30/06/2029 | 1,43 | 1,43 | 0,55 | 0,55 |
| Venta · Base 30/12/2028 · Downside 30/06/2029 | 14,82 | 14,82 | 3,81 | 3,81 |
| **Total cobrado** | **19,10** | **19,10** | **6,80** | **6,80** |
| Sin recuperar al cierre | 0,00 | 0,00 | 11,39 | 11,39 |

El resumen de una página muestra cada aporte adicional por fecha. Las cifras se redondean después del cuadre. En Base, el GP cobra USD 1,82 de catch-up por USD 10 propios, incluido en la venta. Equivale a USD 0,36 por USD 10 iniciales del proyecto. En Downside queda capital sin devolver y el catch-up pagado es cero.

## Términos del ensayo

La [ficha D170](../templates/synthetic-gp-catch-up-terms-D170.json) queda vinculada por huella a los términos D169. D169 conserva aportes y remanente 80 % LP / 20 % GP y preferente LP del 8 % anual simple. D170 inserta un tramo que destina el 100 % de la caja disponible al GP, una vez devuelto el capital y pagado el preferente LP devengado, hasta que el catch-up alcance el 20 % de la suma de preferente LP y catch-up GP. Si P es el preferente acumulado pagado, la meta acumulada es P × 20 % / (1 − 20 %). Cada pago se limita al saldo de esa meta y a la caja disponible. Después se reparte el remanente 80/20.

Con catch-up completo, los porcentajes sobre la ganancia coinciden con las participaciones de aporte de este ensayo. Por eso ambos roles tienen el mismo cobro total por USD 10 propios. Se comprobó un caso adicional con caja que alcanza para pagar el preferente y la mitad del catch-up. El saldo GP queda registrado y el remanente es cero.

## Verificación

B16 reproduce D166. Se concilian todos los movimientos y se comprueba que la devolución de capital y el preferente sean idénticos a D169. Cinco pruebas dejan PENDING ante ficha ausente, porcentaje faltante o inválido, huella D169 distinta u orden incompatible. Un 0 % explícito reproduce D169. El retorno personal real sigue PENDING hasta contar con términos aplicables y verificados.

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_worksheet_gp_catch_up_D170.py --output /tmp/miniuw-d170
```

Usá el [runtime OCR del piloto](workbook-plan-scan-D131.md). Agregá `--package` para auditar un D166 guardado.
