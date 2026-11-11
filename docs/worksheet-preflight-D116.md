# Revisión de la planilla al recibirla

El comando `preflight` lee una copia XLSX sintética con el layout `Inputs`. Identifica el caso y el corte en B3 y E3, y revisa cinco celdas que ya usa el perfil de refinanciación y venta. El checklist indica qué se recibió, dónde está, qué cálculo afecta y qué corrección hace falta. Conserva el hash del archivo. La corrida financiera y la decisión permanecen PENDING.

| Celda | Dato | Qué condiciona |
| --- | --- | --- |
| Inputs!C66 | Cap de refinanciación | Valor de refinanciación y capacidad LTV |
| Inputs!C67 | Cap de salida | Valor de salida y cobro de venta |
| Inputs!C68 | Costo variable de venta | Neto de venta y mínimo de recuperación |
| Inputs!C71 | LTV máximo | Capacidad por valor del activo |
| Inputs!C72 | DSCR mínimo | Capacidad por cobertura de deuda |

- Si C68 está vacía, el checklist pide completar el dato. Si contiene cero literal, conserva el cero.
- Si C72 contiene una fórmula con caché, se conservan ambos como evidencia y el dato queda PENDING.
- Si B3 o E3 difieren del caso o corte declarados, el checklist muestra ambos valores y pide confirmar la copia correcta.
- Si C67 contiene un cap cero, el checklist indica que el valor queda fuera del dominio de la valoración de salida.

El alcance es el perfil sintético D45/D63. La conexión de los demás campos, la hoja real de métricas de Lorena y su aplicación al piloto quedan pendientes. La salida del chequeo identifica el problema en la planilla original. Las correcciones corresponden a una copia nueva.

```bash
PYTHONPATH=src python3 tools/miniuw_worksheet_v1.py preflight planilla-sintetica.xlsx --deal-id SYNTHETIC-integrated-cash-demo --snapshot 2027-07-01T12:00:00Z
PYTHONPATH=src python3 tools/check_worksheet_preflight_D116.py
```

El segundo comando reproduce los casos con planillas archivadas en el repositorio.
