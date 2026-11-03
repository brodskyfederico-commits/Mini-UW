# Mini-UW v1 con calendarios de seguro e impuesto

La entrada reúne el expediente completo v1, los calendarios suministrados de costo/cuotas, su mapa a gastos y pagos, y el registro de fuentes. El retorno se muestra únicamente cuando todos concilian y las fuentes están actuales al UTC declarado. El [contrato técnico](technical-implementation-T90-T92.md) conserva los límites financieros y de autoridad.

| Entrada | Contenido |
|---|---|
| `schema` | `miniuw.synthetic-v1-scheduled-expense-case.v1` |
| `base_case_utf8` | Bytes UTF-8 exactos del expediente v1, incluidos sus 55 campos, criterios y fuentes |
| `schedule_sources_utf8` | Calendarios completos de cada seguro/impuesto; costo, períodos/fracciones, cuotas con fecha/importe/fuente |
| `binding_utf8` | Hashes del expediente/calendarios, concepto/clase y mapa explícito cuota → pago/período |
| `registry_utf8` | Registro de todos los requisitos de fuente y evidencia T46; 41 vínculos en el ejemplo |
| `as_of_UTC` | Mismo instante UTC explícito que el expediente base |

Cada calendario usa `miniuw.synthetic-expense-schedule.v1`. El costo se multiplica por fracciones suministradas con base; la duración en días no define el reparto. Las fechas particionan toda la ventana operativa. Una cuota se vincula a un pago con la misma fecha e importe; este perfil no interpreta pagos tardíos, anticipados o parciales. Un impuesto cero exige datos e inventarios expresos, sin omitir el concepto. Sólo se admite una ventana completa, sin pasivos/prepagos iniciales o finales y con liquidación íntegra dentro de ella. La suficiencia de cobertura y las fechas/reglas reales requieren evidencia y revisión futura.

Con Python 3.11 o posterior y las dependencias de `requirements-reference.txt` instaladas, desde la raíz del repositorio:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python tools/scheduled_miniuw_v1.py run templates/miniuw-v1-scheduled-expense-case.json --output /tmp/miniuw-scheduled-demo
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python tools/scheduled_miniuw_v1.py audit /tmp/miniuw-scheduled-demo
```

La carpeta contiene `case.json`, `results.json`, `execution-evidence.json`, `MiniUW_v1_Resumen.pdf`, `report-manifest.json`, `audit.json`, `schedule-review.txt` y `package.json`. El PDF tiene exactamente una página. Un caso estructuralmente válido pero bloqueado puede generar su informe PENDIENTE con código 0; JSON/perfiles no admitidos, artefactos alterados o imposibilidad de representar la página devuelven código 2. Usar una carpeta nueva por revisión; reintentos idénticos verifican bytes y salidas distintas/incompletas no se sobrescriben.

La [demostración guardada](review/miniuw-v1-scheduled-expense-example/package.json) conserva aportes1.400, cobros778 y resultado−622. La [revisión de impuesto4](../templates/miniuw-v1-scheduled-tax-four-case.json) suministra dos gastos/pagos de2, nuevas fuentes compatibles y deja cobros774/resultado−626. Estas cifras son experimentos sintéticos; no aplican una ley fiscal o un reparto personal. Modificar una fuente exige evidencia compatible explícita: el sistema no renueva su vigencia.

Si falla una cuota, período, fuente o vínculo, `schedule_blockers` explica el motivo y se retiran historia actual, EM y valores derivados del PDF. Los insumos, hashes y pruebas históricas siguen recuperables. El registro vigente no equivale a autenticidad profesional o autoridad real. Los criterios del deal conservan sus pendientes; no hay despliegue, admisión automática a Full UW o decisiones reales.
