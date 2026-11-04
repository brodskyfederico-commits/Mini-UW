# Ejecutar y recuperar Mini-UW con la página del inversor

Este comando local integra el renderer T96 y el transporte T97. Usa expedientes sintéticos del perfil ya soportado. No contacta servicios, evalúa deals reales ni despliega bots. Decisión PENDING, criterios nuevos/vacíos y pendientes financieros conservados.

Con Python y las dependencias de `requirements-reference.txt` ya instaladas, desde la raíz del repositorio:

```bash
PYTHONDONTWRITEBYTECODE=1 python tools/investor_miniuw_v1.py run \
  templates/miniuw-v1-policy-renewal-case.json --output /tmp/miniuw-inversor-ejemplo
PYTHONDONTWRITEBYTECODE=1 python tools/investor_miniuw_v1.py audit /tmp/miniuw-inversor-ejemplo
```

El directorio de salida debe ser nuevo o contener exactamente el mismo paquete. Una entrada distinta, una carpeta incompleta o un manifiesto alterado se rechazan sin reemplazar su contenido. Para otra revisión, usar otro directorio. Los errores devuelven código2 y un JSON de estado bloqueado/PENDING; no se interpretan como FAIL de inversión. JSON inválido se rechaza antes de crear la carpeta de salida.

| Archivo | Función |
| --- | --- |
| `case.json` | Bytes exactos de la entrada |
| `results.json` | Resultado financiero T94 sin cambios |
| `execution-evidence.json` | Bundle T97, con prueba padre T95 y manifiesto T96 |
| `MiniUW_v1_Resumen.pdf` | Un solo PDF de una página con aportes/cobros/neto anual |
| `report-manifest.json` | Fuente de cada frase, versiones y huellas del reporte |
| `audit.json` | Comprobación técnica, sin aprobación financiera |
| `schedule-review.txt` | Diagnóstico de seguros y bloqueos; retira totales actuales si corresponde |
| `package.json` | Inventario exacto de los siete archivos anteriores |

La auditoría comprueba inventario, bytes y hashes y después reconstruye el paquete desde la entrada. Rehashear el inventario después de adulterar un resultado no lo vuelve válido. `execution-evidence.json` permite recuperar el caso, resultado y reporte con código/definiciones compatibles:

```python
from pathlib import Path
from miniuw_foundation.investor_output_artifacts import recover_investor_output_bundle

recovered = recover_investor_output_bundle(
    Path('/tmp/miniuw-inversor-ejemplo/execution-evidence.json').read_bytes())
assert recovered.run.payload['decision'] == 'PENDING'
# recovered.case_raw, recovered.run y recovered.report son objetos reproducidos.
```

Para la API Python, el paquete `miniuw_foundation` debe estar instalado o `src` incluido en `PYTHONPATH`, como en la ejecución de pruebas del repositorio. No hace falta entregar varios PDFs: el resto es evidencia interna. La recuperación de un caso vencido conserva su estado bloqueado y el retiro de cifras; no renueva fechas o evidencia automáticamente.

[Ejemplo completo de ocho archivos](review/miniuw-v1-investor-package-example/) · [PDF](review/miniuw-v1-investor-package-example/MiniUW_v1_Resumen.pdf) · [Comprobación reproducida](review/investor-output-package-validation-T97.json) · [Alcance T97](technical-implementation-T97.md).

El CLI anterior `renewal_miniuw_v1.py` conserva el renderer T95 y no acepta este esquema como si fuera su bundle. Los originales y resultados previos permanecen intactos. Este mecanismo guarda evidencia técnica local; los datos reales, autoridad, capital/CoC, retorno personal y validación financiera siguen pendientes. No es recuperación de la aplicación histórica o infraestructura productiva.
