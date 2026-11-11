# Recepción de cuadros de superficies declaradas

Este control compara dos revisiones sintéticas de un cuadro de superficies y unidades. Conserva el identificador del documento, la lámina, la revisión, la fila indicada por la fuente y la ubicación exacta del dato en el archivo, junto con su SHA-256. Los grupos se cotejan por su identificador, incluso si cambian de orden.

| Dato declarado | Unidad | Dónde puede usarse tras la revisión |
|---|---|---|
| Unidades del grupo | Unidades | Capacidad residencial del grupo. |
| Superficie rentable por unidad | ft² rentables por unidad | Ingreso residencial cuando la renta se expresa por ft² rentable. |
| Superficie bruta del edificio | ft² brutos | Presupuesto cuando la base por GSF, el alcance y la condición de uso de C36 están verificados. |

Las unidades y las superficies representan datos distintos. El contrato de C7 exige superficie rentable por unidad para la rama por ft². El contrato de C36 condiciona el uso de GSF a la base y al caso definidos. [Contratos de renta y presupuesto](current-structure/MiniUW_Contratos_Financieros_Prioritarios_D09.md)

En la revisión de ejemplo, la superficie rentable del grupo 1BR-A baja de 710 a 690 ft² por unidad. El grupo 2BR-A declara cero unidades. La superficie bruta queda sin declarar y la cifra de la revisión anterior sigue visible como historial. Cada cambio o dato faltante queda pendiente de revisión.

Ejecutá estos comandos desde la raíz del repositorio.

```bash
PYTHONPATH=src python tools/plan_schedule_D105.py check
PYTHONPATH=src python tools/plan_schedule_D105.py compare \
  templates/synthetic-plan-schedule-D105-A.json \
  templates/synthetic-plan-schedule-D105-B.json
```

La comparación registra evidencia candidata. La lectura de DWG, la conciliación de las lecturas del plano y su aprobación financiera quedan pendientes. El resultado no incorpora datos al presupuesto ni al flujo de caja, y el retorno por USD 10 permanece PENDING. [Alcance de lectura de planos](MiniUW_v1_Dots_y_Bots.md)
