# T60 — recuperación portable del recorrido sintético

El paquete JSON contiene bytes UTF-8 exactos de las fuentes sintéticas, calendarios, vínculos y resultados T58/T36/T59. Incluye NOI/caja por período, cierres/deudas, manifiesto, sizing del refi, ledger operativo de referencia y ledger ampliado. Exportar exige reproducir el recorrido completo, incluso si está bloqueado. El paquete no ejecuta instrucciones, fórmulas externas, código serializado ni rutas de archivos.

Al recuperar se comprueban tamaño, esquema exacto, inventarios acotados, claves JSON únicas y versiones compatibles. Se reconstruye cada productor desde sus fuentes y después se reproduce T58, T36 y T59, comparando resultados completos y hashes. Cambiar una cifra y actualizar un hash no basta. Un paquete bloqueado sigue bloqueado tras recuperarse; no adquiere aprobación por guardarse o cargarse.

Es un transporte de evidencia sintética para este perfil, no respaldo de bases runtime ni recuperación del VPS. No autentica pagos/documentos/activos, cambia criterios, habilita publicación financiera o despliega servicios. La recuperación usa sólo los módulos locales compatibles y conserva los límites financieros de los productores.
