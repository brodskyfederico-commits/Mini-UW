# Estructura de ejecución sin dependencia de una respuesta experta

El diseño puede continuar por capas: entradas/evidencia, contratos de módulos, eventos de caja/deuda, cantidades/unidades y estados; después cálculo candidato y comparación. No se exige una revisión para redactar o probar esas interfaces. Las elecciones financieras faltantes quedan como entradas explícitas, no se sustituyen por números ni detienen el diseño de partes independientes.

`module-execution-design.json` identifica etapas M1–M9, entradas, salidas y dependencias. M8 puede reejecutar dependencias bajo cada escenario; un grafo de etapas no resuelve el ciclo financiero de M5. Se distinguen el bloqueo de una cantidad, el estado de un módulo y la imposibilidad de emitir una decisión completa de deal.

`templates/project-draft-empty.json` separa 55 campos originales en entradas del proyecto, entradas de financiación y alternativas solicitadas; añade un espacio independiente para las diez métricas de criterios. No contiene umbrales, shocks, tasas, moneda o respuestas expertas. La clasificación “financiación” identifica consumidor, no prueba que el banco lo haya confirmado. La ausencia de precio/otra deuda/reserva o un resultado indefinido no se convierte en cero.

La plantilla está intencionalmente incompleta: no es una ejecución financiera ni un contexto válido listo para motor. `run_ready=false`, criterios/políticas/parámetros vacíos y autorización no concedida. Las únicas restricciones completadas son instrucciones actuales del usuario: faltantes quedan PENDIENTES, PDF externo de una página, Full UW diferido y producción deshabilitada. Eso no equivale a completar Q1–Q20 en nombre de Lorena.

Cada nueva revisión de reglas/datos altera sus dependientes y conserva lo viejo como histórico. Una modificación sólo de criterios puede preservar caja independiente, pero obliga a nuevas comparaciones/valoraciones dependientes. Los protocolos de integridad y contratos de registro definen cómo implementarlo más adelante; no son todavía persistencia, autenticación ni liberación de producto.

R02 queda intacto para recibir observaciones; el trabajo posterior se enlaza al mismo registro de fuentes y al historial Git, sin atribuir al profesional una revisión que no hizo.
