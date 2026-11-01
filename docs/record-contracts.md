# Registros de evidencia, costo, caja, deuda, criterios y ejecución

Se proponen seis contratos estructurales complementarios a M1–M9: partida de costo, evento de caja, movimiento de principal de deuda, criterio, escenario e instantánea de ejecución. Usan el vocabulario común; no contienen datos financieros reales ni defaults de la casa. Archivo por familia en `schemas/`.

Costo: ID económico y vínculo contractual permiten distinguir alcance de representaciones documentales. C39 o una etiqueta “contingencia” no prueba que la base esté definida. Inclusión no resuelta no se interpreta como costo cero ni se suprime por igual monto.

Caja: cada aporte/distribución es bruto, tiene ID, cuentas, período/calendario, contexto y fuentes. Reserva, deuda, operación y venta se clasifican por movimiento, no por signo neto inferido. Principal capitalizado se registra en deuda, con vínculo a caja sólo cuando corresponde; no crear un cash draw ficticio por interés sin caja.

Criterio: métrica/definición, contexto, condición, operador, threshold y aplicabilidad expresos; exclusión exige razón y referencia de regla. Una regla referenciada no acredita aprobación o autoridad. La aplicación de agregación exige además una política vigente; una fila de criterio no decide por sí sola el deal.

Escenario: bindings explícitos a valores/versiones, transformaciones con unidad y referencias, criterios propios y sin herencia de lo no especificado. Un conjunto vacío no significa completitud: reglas de requerimiento/applicabilidad y C1 siguen siendo semántica separada. No rellenar automáticamente Base ni Downside.

Instantánea: versiones explícitas de documentos/definiciones M1–M9 y referencias de escenario/criterio/regla. “Estructuralmente completo” no demuestra cálculos vigentes, autenticación o revisión financiera. Persistencia, idempotencia y publicación atómica siguen siendo trabajo futuro no activado.

Conflictos: el valor conserva al menos dos afirmaciones literales y sus fuentes, además de las causas. No se decide un ganador. La propagación puede enlazar las causas al registro de origen sin sobrescribir las afirmaciones originales. No aplicable no se transforma en cero.

Estas familias son una interfaz mínima agregada, no el desglose final del underwriting, modelo fiscal o contrato bancario. Los validadores prueban forma y relaciones genéricas con fixtures sintéticos; no aprueban semántica del negocio ni permiten transacciones o decisiones reales.
