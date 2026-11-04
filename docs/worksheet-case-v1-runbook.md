# Hoja sintética y expediente T103

Coteja los55 valores del diseño original contra las declaraciones del caso completo. Identifica diferencias por celda y campo. Una coincidencia conserva la proyección condicionada previa; una diferencia, fórmula/error o vínculo incorrecto retira las cifras actuales. No completa campos ni adopta valores de la hoja. Los54 mapeos financieros pendientes del ejemplo siguen pendientes.

Desde la raíz del repositorio, Python y dependencias de `requirements-reference.txt`:

```sh
PYTHONDONTWRITEBYTECODE=1 python tools/worksheet_case_miniuw_v1.py run \
  templates/miniuw-v1-policy-renewal-case.json \
  templates/worksheet-case-matched-T103.xlsx \
  --binding templates/worksheet-case-matched-T103.json \
  --output /tmp/miniuw-T103-hoja
PYTHONDONTWRITEBYTECODE=1 python tools/worksheet_case_miniuw_v1.py audit /tmp/miniuw-T103-hoja
PYTHONDONTWRITEBYTECODE=1 python tools/check_worksheet_case_T103.py
```

El paquete contiene nueve archivos: caso, Inputs.xlsx, vínculo, resultados, evidencia portable, un PDF actual, manifiesto del informe, comprobación técnica y package.json. El ejemplo está en `docs/review/miniuw-v1-worksheet-case-example/`. La recuperación repite ambos lectores y la cadena financiera desde sus fuentes; no acepta alteraciones por rehashearlas. Reintento idéntico verificado, otra salida exige otro directorio. Uso local de un escritor; sin publicación o despliegue.

El perfil exige marcador sintético G1 y el diseño exacto T06. B3=ID del caso y E3=UTC completo son convenciones explícitas de este ensayo. El vínculo lleva hashes exactos, contexto, ID, revisión, UTC y referencia; no autentica autoría. Una hoja real de Lorena requiere adaptación y evidencia posteriores. El marcador no acredita que una hoja desconocida contenga datos ficticios.

Se distinguen número, texto, cero, vacío, ausencia, fórmula/caché y error. Sólo las celdas numéricas con representación decimal admitida por T07 se cotejan como racionales exactos; texto numérico y formatos no admitidos no se convierten por conjetura. Unidades, requisitos y notas originales se preservan; `$` no define moneda ni una coincidencia define el consumidor financiero. Un nombre en F no autentica revisión.

Los cuatro ensayos reproducen coincidencia con54 faltantes, cero discrepante, fórmula con caché y hoja identificada con otro caso. Todos conservan decisión PENDING. Una hoja coincidente tampoco recupera cifras retiradas por fuentes financieras vencidas. [Definición y límites](technical-implementation-T103.md).
