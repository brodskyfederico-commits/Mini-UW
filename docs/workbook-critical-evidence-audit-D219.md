# Si invierto USD 10, ¿cuánto cobro y cuándo?

D219 audita el respaldo documental de una corrida sintética archivada. El auditor es de sólo lectura. Los importes y fechas por USD 10 se pueden consultar en el paquete reproducido por B16. El dictamen real y el retorno histórico quedan PENDING.

## Denominador y señal

La unidad de conteo es un **dato crítico por expediente y escenario**. Un dato compartido se cuenta una vez aunque lo lean varios bots o tenga más de una cita. El inventario sintético fija 48 datos:

| Grupo | Datos | Bots en el cotejo |
| --- | ---: | --- |
| GBA conciliada entre A101, A601 y cotización | 1 | B03, B05, B06, B07, B08, B09 |
| Límite de pisos y vigencia de la copia oficial | 1 | B10, B11 |
| Costo vertical de GC en Base y Downside | 2 | B08, B09 |
| Crédito de obra y permanente, siete términos por combinación de crédito y escenario | 28 | B08 |
| Rentas, concesiones, absorción, cap de salida y seguro en ambos escenarios | 16 | B08 |

Un dato con una marca verde incompatible con la referencia independiente se registra como **FALSE_GREEN**. El resultado señala bot, campo, cita, ruta del dato y motivo. Se comprueban el valor y la unidad o convención aplicable, página, localizador, huella y revisión designada. Los datos sin verificación completa quedan PENDING. Un verde válido de un lector puede coexistir con un dato PENDING si la cadena aún debe conciliarlo. La falta de una fuente afecta los datos cuyos verdes dependen de esa fuente.

Los valores y localizadores del inventario se cotejaron contra las líneas originales de las páginas sintéticas D137/D156/D157, los rangos de mercado del caso D200 y las planillas de ensayo. Las huellas fijan los archivos de prueba y permiten detectar si cambian. La auditoría compara el resultado contra ese inventario y comprueba el vínculo con la revisión externa. B16 conserva su función de reproducir la corrida.

## Resultado y reproducción

La corrida vigente sintética produce 48 verdes respaldados y cero falsos verdes. La prueba automatizada altera un respaldo por cada dato y detecta los 48. Los controles adicionales cubren página equivocada, cita ausente, unidad incompatible, lectura omitida, hoja duplicada, huella distinta, PDF ausente y revisión anterior. Se comprueba que un faltante legítimamente pendiente y un dato independiente respaldado conserven sus estados. La cifra 0/48 corresponde a esta muestra y perfil documental sintéticos. El cotejo de falsos verdes sobre documentos reales y otras familias de datos requiere inventarios independientes para esas muestras.

Con el [runtime OCR configurado](workbook-plan-scan-D131.md), ejecutar desde la raíz del repositorio:

```bash
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 -m unittest -v test_worksheet_critical_evidence_D219

PYTHONPATH=src:tests python3 tools/audit_worksheet_critical_evidence_D219.py /ruta/expediente-sintetico \
  --current-revision /ruta/revision-sintetica-designada.json
```

El comando imprime JSON por dato y devuelve 0 si todos los datos del inventario tienen verde respaldado, o 2 si queda PENDING o detecta un falso verde. El [inventario](../templates/synthetic-critical-evidence-D219.json) se conserva versionado con sus valores, fuentes y alcance.
