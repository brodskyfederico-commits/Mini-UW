# Ingreso documental de planos · D208

El comando `intake` del piloto Mini-UW coteja un set de arquitectura con capa de texto, una carta de revisión y un cuadro de superficies por tipo cuando están disponibles. Es una etapa de revisión antes del cálculo. Usa PyMuPDF 2.0 para leer las láminas y guarda el nombre, la huella SHA-256 y el número de páginas de cada PDF.

```bash
python3 -m pip install -r requirements-reference.txt PyMuPDF==2.0
PYTHONPATH=src:tests python3 tools/worksheet_preliminary_pilot_D205.py intake \
  /ruta/Arquitectura.pdf --narrative /ruta/Carta.pdf \
  --area-schedule /ruta/CuadroAreas.csv --output /ruta/cotejo.json
```

El CSV usa los encabezados `unit_type,area_sf` y una fila por tipo. Las comas de miles deben ir entre comillas en el CSV. El perfil busca A1.0 y las láminas de piso A2 del índice G0.0 y reconoce sus bloques de texto y rótulos de unidad. Coteja los conteos declarados, los identificadores únicos, la mezcla por dormitorios, el metraje comercial y los tipos sin área declarada. Cada discrepancia guarda las ubicaciones disponibles. Los hallazgos no sustituyen ningún valor de origen.

La corrida admite documentos de hasta 200 páginas y 256 MiB por PDF. La lectura exige las etiquetas de este perfil y revisa sus textos. El cálculo geométrico, los escaneos sin texto y otros formatos de lámina requieren un perfil validado. `READ` indica que el cotejo documental ejecutado quedó sin hallazgos. Base y Downside mantienen caja y retorno por USD 10 en `PENDING`, con dictamen `PENDING` y ranking vacío.

```bash
PYTHONPATH=src:tests python3 tools/check_worksheet_documentary_intake.py
PYTHONPATH=src:tests python3 tools/check_worksheet_preliminary_pdf_D206.py
```

Se verificó en el VPS un set de 57 páginas y se reprodujeron las discrepancias de unidades y áreas desde los documentos. El ensayo sintético cubre páginas fuera de orden, lámina faltante o duplicada, rótulo incompleto, diferencias de áreas y conteos y bloqueo de los flujos. Los documentos reales, la transcripción y el resultado de esta corrida quedan en el expediente local.
