# Si invierto USD 10, ¿cuánto cobro y cuándo?

**Primer piloto real del Mini-UW v1 · PENDING**

El paquete queda listo para recibir un expediente. Los flujos reales, el dictamen y el retorno personal siguen PENDING. La prueba sintética de referencia D188 muestra cómo se presentan aportes, cobros fechados y saldo sin recuperar. [Ejemplo de una página](../MiniUW_Preliminar_Obra_Etapas_D188.pdf).

## Entregables

- [Pedido para Lorena en PDF](MiniUW_Pedido_a_Lorena_D190.pdf) y [texto editable](Pedido_a_Lorena.md).
- [Control del piloto, criterios, responsables y cotejo por USD 10](MiniUW_Control_y_Cotejo_D190.xlsx).
- [Referencia de los 55 campos y ocho complementarios](../MiniUW_Planilla_55_Campos_Revision_Profesional_D174.xlsx).
- [Acta de alcance congelado y mínimos de PRELIMINAR](../../preliminary-pilot-readiness-D189.md).

## Criterios y responsables por confirmar

| Pendiente | Quién confirma | Qué evidencia cierra el pendiente |
| --- | --- | --- |
| Autorizar los datos y designar funciones | Aprobador por identificar | Autorización sobre el expediente y la revisión, y responsables nombrados para evidencia oficial, criterios y cotejo financiero. |
| Datos Base y Downside | Lorena y dueños de fuente | Dos Inputs versionados, complementarios y respaldos compatibles. La autoridad de Lorena sobre criterios se documenta por separado. |
| SRC-02 · Ocupación de equilibrio | Responsable de criterios por designar | Definición, base de renta, reservas, servicio anual, desglose C14 si se publica ocupación física, aplicabilidad y aprobación. |
| SRC-03 · RLV | Responsable de criterios por designar | Criterios vinculantes, deuda fija o política elegida, tratamiento de C33, dominio, límites PASS/previo a FAIL y aprobación. |
| NOI, YoC, spread y CoC | Responsable de criterios por designar | Bases y períodos. Documentar la base del cap comparable para spread. Mantener identificadas las bases de NOI bancario y valoración. |
| Dictamen formal | Responsable de criterios por designar | Inventario de diez métricas por escenario, aplicabilidad, operadores, umbrales, banda, versión, vigencia y agregación. La banda intermedia sigue PENDING. |
| Ranking PRELIMINAR | Responsable de criterios por designar | Mínimos, comparabilidad y métrica de prioridad. El múltiplo de Downside es la convención ensayada con datos sintéticos. PRELIMINAR mantiene el dictamen formal PENDING. |
| Evidencia oficial | Custodio por designar | Copias, jurisdicción, cita y fecha. |
| Conciliación independiente | Revisor financiero por designar | Referencia separada, cotejo por fecha y evidencia de resolución de diferencias. |

Las condiciones bancarias de obra y refi se registran con su fuente y aplicabilidad. Se mantienen separadas de los umbrales de inversión. Los valores sintéticos quedan en sus expedientes de ensayo.

## Cómo cotejar el retorno por USD 10

1. **Fijar el corte.** Registrar ID, revisión, fecha, moneda y huellas de los archivos. Confirmar que Base y Downside pertenezcan al mismo expediente. Guardar las fuentes aplicables y la versión del cálculo independiente. Verificar autorización antes de usar datos reales.
2. **Construir la referencia independiente desde fuentes.** Calcular primero en USD del proyecto. Conciliar adquisición y usos de obra, aportes, desembolsos, intereses, comisiones, saldos, capacidad por menor límite aplicable, cancelación de obra, reserva, caja operativa, venta y saldo de deuda. Revisar fechas, signo y naturaleza de cada movimiento. Registrar la referencia antes de cotejar con el motor.
3. **Escalar y comparar.** Multiplicar cada movimiento bruto por `10 ÷ aporte inicial verificado del escenario`. Mantener aportes y cobros separados aunque coincidan en fecha. Comparar monto y fecha de cada fila y su fuente. Conciliar cobros de refi, operación y venta, aportes adicionales, resultado neto, saldo sin recuperar y múltiplo. Mostrar patrimonio retenido aparte. Para TIR, contrastar el intervalo y su grilla o convención temporal.
4. **Cotejar criterios y el PDF.** Comparar los valores calculados por el Mini-UW y por la referencia, aplicar la misma revisión de criterios, verificar el motivo de cada PENDING y confirmar que el informe de una página muestre cuánto se aporta y cobra y cuándo. Si falta una fuente de caja, se retiran cifras dependientes. Si sólo falta un criterio, la caja verificada puede quedar visible con la comparación PENDING.
5. **Resolver y repetir.** Registrar diferencias sin redondear, causa, responsable y evidencia. Toda corrección crea una nueva revisión y vuelve a ejecutar los cálculos dependientes. Conservar historial. El revisor confirma qué diferencias se resolvieron y cualquier tolerancia aplicable con fuente y aprobación. El piloto sigue PENDING ante una brecha abierta.
6. **Cerrar el piloto técnico.** Un resultado reproducible y revisado puede documentar un FAIL o un PENDING fundado. Cualquier PASS real requiere criterios, evidencias y aprobación vigentes. La aprobación de paso a Full UW se acredita por separado.

El [cotejo D179](../../workbook-independent-reconciliation-D179.md) y sus [736 filas sintéticas](../MiniUW_Cotejo_Independiente_D179.csv) muestran el método de control. La plantilla D190 ayuda a comparar ambos resultados. La referencia financiera se construye desde los documentos del caso.
