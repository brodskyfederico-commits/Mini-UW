# Si invierto USD 10, ¿cuánto cobro y cuándo?

El ensayo sintético conserva los flujos conciliados de D191. Base aporta USD 4,87 adicionales y cobra USD 18,06 hasta el 30/12/2028. Downside aporta USD 8,19 adicionales y cobra USD 6,08 hasta el 30/06/2029. Quedan sin recuperar USD 0,00 y USD 12,11, respectivamente. El [PDF de una página](review/ensayo-D190-D191/MiniUW_Informe_USD10_D191.pdf) detalla las fechas de cada aporte y cobro del equity agregado del proyecto.

## Criterios entregados por Lorena

La [planilla de criterios](../templates/MiniUW_Criterios_PASS_FAIL_Lorena.xlsx) pide operadores y umbrales vigentes. El equipo del proyecto prepara los Inputs y los respaldos. La lectura toma las columnas amarillas E–H y conserva su ubicación, el texto original y la huella del XLSX. Los números de B–D quedan como referencia histórica. Las notas de base, vigencia y política se conservan como declaraciones para revisión.

El cotejo reconstruye primero el expediente de Base y Downside con B16 y comprueba la revisión designada. Así se puede reproducir la comparación desde el XLSX recibido y la corrida financiera. La prueba aplica aritmética exacta a las definiciones del perfil D181, incluida la TIR como intervalo y el aporte de refi en USD del proyecto. La coincidencia de unidad permite comparar. Confirmar que coinciden también definición, denominador y período sigue siendo parte de la revisión.

| Entrada | Efecto de la prueba |
| --- | --- |
| Criterio completo y unidad compatible | Se observa PASS o FAIL en la fila, con el localizador de la regla. |
| Cero explícito | Se coteja como cero. El vacío deja PENDING. |
| Downside con «Sin FAIL» | Se verifica PASS; su incumplimiento queda PENDING. La política vigente queda por confirmar. |
| Banda intermedia, umbrales solapados o TIR que cruza un límite | La fila requiere revisión. |
| Umbral en % cuando el perfil calcula USD | PENDING por unidad, sin conversión del denominador. |
| Fórmula, formato alterado o revisión histórica | Se rechaza la lectura para la revisión vigente. |
| SRC-02, SRC-03 o «No aplica» declarado | PENDING hasta verificar definición o aplicabilidad. |

## Reproducción en el VPS

Usar [el entorno de OCR fijado](workbook-plan-scan-D131.md) y las dependencias de referencia.

```sh
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/check_lorena_criteria_D192.py --output /tmp/miniuw-d192
OMP_THREAD_LIMIT=1 PYTHONPATH=src:tests python3 tools/preview_lorena_criteria_D192.py /tmp/miniuw-d192/Expediente \
  --current-revision templates/synthetic-workbook-current-revision-D181.json \
  --criteria /tmp/miniuw-d192/Criterios_Sinteticos_D192.xlsx
```

El cotejo se agrega como JSON interno. El estado del piloto y la decisión permanecen PENDING. El perfil D181 mantiene su PDF y dictamen histórico. El primer caso real requiere sus documentos, el cotejo financiero y criterios auténticos y compatibles. SRC-02 y SRC-03 conservan sus definiciones candidatas en [D184](workbook-performance-policy-D184.md).
