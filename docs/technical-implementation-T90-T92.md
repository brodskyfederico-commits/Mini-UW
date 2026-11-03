# T90 a T92 Seguros e impuestos por período en el Mini-UW

## T90 Calendario de costo y cuotas suministrado

El perfil sintético recibe contexto, moneda, ID de seguro o impuesto, costo total declarado, ventana de servicio o liquidación, fracciones explícitas por período y cuotas con fecha/importe/fuente. Las ventanas ordenadas particionan exactamente el intervalo y las fracciones no negativas suman uno. El gasto de cada período es costo total por fracción suministrada. No deduce fracciones de días, devengo contable aplicable o reglas fiscales. Un cero requiere valor e inventarios completos; una cuota o fracción faltante bloquea todos los importes exportables.

Las cuotas brutas no negativas tienen ID y fuente únicos, fecha dentro de la ventana semiabierta y suma igual al costo total. Es un perfil reducido de ventana completa con liquidación íntegra dentro de ella. Impuestos posteriores a venta, saldos iniciales/finales fuera del intervalo, pólizas múltiples/renovaciones, créditos, reembolsos o comisiones requieren otro perfil; no se inventan. Los límites de aritmética exacta retiran todos los totales ante desborde.

El seguro se interpreta como un calendario declarado de costo: no acredita suficiencia de cobertura, aseguradora, vigencia contractual, límites, deducibles o exclusiones. El impuesto es una liquidación sintética suministrada: no certifica autoridad, ley, exención o vencimiento real. Cada referencia de fuente permanece declarada.

## T91 Vinculación con gastos y retorno completo

Una entrada versionada contiene los bytes exactos del expediente v1, fuentes T90, binding y registro T46. Se reconstruye T85 desde sus fuentes; cada seguro e impuesto del detalle T76 debe tener exactamente un calendario. Se exige mismo concepto, clase, contexto, moneda, todos los períodos y las fechas de caja. Cada gasto calculado T90 coincide con el devengo declarado T76 ya conciliado con NOI; cada cuota se vincula expresamente a un pago por ID/período, con importe y fecha idénticos. El perfil no resuelve pagos anticipados/tardíos ni parciales: una diferencia requiere nueva información y conserva PENDING, sin inventar penalidad o tolerancia.

El calendario no vuelve a descontar gastos ni pagos. Sólo cuando toda la cadena y todos los calendarios son compatibles se conserva el retorno original del expediente. Los cuatro saldos por concepto y su continuidad siguen siendo suministrados y controlados por T76/T77; este nuevo productor no los deriva ni compensa un seguro con un impuesto. La ventana completa exige apertura y cierre por pagar/prepagado cero para cada calendario; no omite obligaciones fuera de su alcance.

La vista actual exige además todos los requisitos de fuente T84, el expediente v1 completo, cada calendario y el binding al mismo UTC explícito. En el ejemplo son 41 vínculos. Modificar una fuente no renueva evidencia; hashes, localizadores, contexto, estado y fechas deben coincidir. Un fallo retira historia de retorno actual, EM y cifras derivadas del resumen; fuentes y bloqueos se conservan para recuperación. El resultado base queda como referencia histórica por hash, sin ser presentado como una aprobación vigente en el nuevo perfil.

## T92 Recuperación y una página

El paquete acotado conserva la entrada UTF-8 exacta, resultado, versiones de motores y definición. Recuperar exige reconstrucción íntegra: cambiar resultados/fuentes y recalcular hashes no evita el replay. Se recuperan casos compatibles y bloqueados. El expediente y los calendarios originales se mantienen intactos; no hay código externo, búsquedas, base runtime o reloj vivo.

Una orden genera ocho archivos: entrada, resultados, evidencia reproducible, PDF de una página, manifiesto de texto/cifras, comprobación técnica, resumen de calendarios y package.json con hashes. El renderer reutiliza exclusivamente la utilidad de composición de página T86 después de reproducir T91; su manifiesto identifica T92 y el resultado con los nuevos controles. El PDF muestra el retorno del proyecto o PENDIENTE con cifras retiradas, sus diez métricas, fechas, base por 10 y bloqueos. Los criterios se conservan expresamente del expediente y no se adoptan umbrales históricos. La comprobación de una página/texto/huellas es técnica determinista; no es auditoría financiera independiente.

La salida completa se materializa desde un directorio temporal hermano, con verificación byte por byte para repetir una salida idéntica y rechazo de salidas diferentes, incompletas o con enlaces simbólicos. Audit comprueba inventario/hash y reconstruye todos los archivos; límites de tamaño, texto y disposición rechazan sin truncar o agregar páginas. No es publicación concurrente productiva o entrega financiera autorizada.

## Ejemplos y pendientes

Un seguro de costo 20 con dos fracciones suministradas de 1/2 produce gastos 10 y 10, con cuotas/pagos declarados 5 y 15. El primer payable 5 y su cancelación posterior se conservan; el calendario no crea otro gasto. El impuesto explícito cero tiene fracciones y cuotas completas vacías, sin convertir faltantes en cero. Esta vinculación preserva aportes 1.400, cobros 778 y resultado −622 del ejemplo anterior.

Una revisión sintética suministra impuesto 2 por período, liquidación total 4, pagos 2 y 2 y nuevas fuentes de NOI/caja/venta/evidencia compatibles. Los cobros pasan a 774 y el resultado a −626; el cambio llega una sola vez al retorno. No se aplica una norma fiscal ni se infieren pagos o financiación.

Las bases personales, capital/equity/CoC, todos los 55 campos conectados, métricas/criterios pendientes, reglas legales/contables, autoridad real, liquidez intraperíodo, perfiles fuera de ventana y validación financiera profesional siguen abiertos. PENDING, sin despliegue ni decisiones reales. Los originales/I01 y las rutas anteriores permanecen preservados.
