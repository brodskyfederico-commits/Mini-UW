# Si invierto USD 10, ¿cuánto cobro y cuándo?

D264 conecta el transporte exacto D263 con la entrada original de la planilla y el dictamen integrado. La corrección evita que un valor válido quede bloqueado sólo por el límite anterior de 256 dígitos de una fracción. No redondea cálculos ni modifica umbrales, reglas de precedencia, fechas o términos bancarios.

## Alcance y activación

El perfil técnico sintético admite una configuración explícita en `rent_inputs.cash_transport`:

```json
{"profile":"miniuw.synthetic-integrated-exact-transport.v1","source_ref":"SYNTHETIC-D264-exact-intake"}
```

Su ausencia conserva el transporte anterior. Una configuración inválida o un algoritmo cuya huella no coincide deja ambas cajas PENDING; no vuelve silenciosamente al motor anterior. La configuración no constituye una autorización de uso real ni de despliegue.

`worksheet_integrated_transport_D264.integrated_engines` reutiliza el transporte aislado D263 y añade un espacio de funciones privado para el comparador escalar. Registra perfil, referencia, huellas de adaptadores/algoritmos y revisión, sin modificar las variables globales del motor original. Los lectores de resultados calculados de D167, D173, D181 y D193 admiten 1.300 dígitos. Las entradas y las reglas conservan sus validadores, unidades y fuentes; el presupuesto aritmético sigue siendo acotado. Ausente no significa cero; un cero explícito se conserva sujeto al dominio de cada variable.

## Prueba dirigida

Pasaron **dos pruebas en 121,454 segundos** en el VPS:

- Compatibilidad: con tasas anteriores, el nuevo transporte conserva exactamente los movimientos fechados y totales por USD 10 de Base y Downside.
- Entrada revisada: C69 numérico de 5,01 % / 6,51 % en los XLSX, documentos bancarios sintéticos escaneados coherentes y nueva confirmación explícita del anexo de debt yield. El interés, el saldo, la cancelación y la caja se recalculan sin redondear; las citas y huellas corresponden a la nueva evidencia.
- El principal de cuota Base supera 256 dígitos y llega a caja y al CoC. El paquete completo se reproduce por B16 como VIGENTE. La configuración inválida bloquea ambos escenarios; las huellas no reconocidas también se rechazan.

Los documentos de prueba incluyen JPEG progresivo, giros y orden de páginas alterado. Se preservan los originales del repositorio; los PDF revisados son fuentes sintéticas nuevas. El generador de pruebas usa Pillow y DejaVu Sans Mono del entorno del VPS, sin conexión a fuentes reales. No rebaja los controles de OCR para hacer pasar el ensayo.

Reproducción, con las dependencias de OCR del VPS en el entorno:

```bash
OMP_THREAD_LIMIT=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests:tools python3 -m unittest -v test_worksheet_integrated_transport
```

Esta prueba dirigida precede a la batería general de cierre. El dictamen real, la evidencia y los criterios sin confirmar mantienen PENDING. Los perfiles de calendario conservan sus horizontes documentados; D264 no implementa por sí mismo un horizonte general de cinco años ni cierra las políticas parciales de D252. No se atribuye retorno personal sin términos de reparto. Respaldo: código, pruebas y documentación; excluye credenciales, expedientes reales y resultados generados.
