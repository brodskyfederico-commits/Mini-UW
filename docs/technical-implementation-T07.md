# T07 — Decodificación numérica exacta con perfiles sintéticos explícitos

T07 convierte representaciones de números en fracciones exactas bajo un perfil de prueba declarado. No adopta definiciones financieras, no valida la economía del deal y no introduce criterios de inversión. La normalización financiera completa sigue pendiente; todos los resultados conservan PENDING y producción desautorizada.

## Contrato de conversión

Cada `NumericProfile` declara explícitamente ID sintético, revisión, campo de input, referencia de definición de fuente, separador decimal, notación, política de espacios, unidad de origen/destino, tipo de cantidad, moneda y período. No hay perfiles predeterminados para los 55 campos. El perfil es una declaración técnica de prueba; su nombre o contenido no constituye aprobación de su significado financiero. Solo se aceptan perfiles para slots de input, sin adoptar los criterios de inversión.

Se admiten notación decimal de punto o coma, con signo y dígitos ASCII, y porcentaje con sufijo explícito. El separador nunca se infiere del texto. No se admiten agrupación de miles, exponentes, NaN/Infinity, fracciones escritas, fórmulas o números ambiguos fuera de la gramática elegida. Los espacios exteriores solo se eliminan cuando el perfil lo exige expresamente. El texto original permanece intacto en las declaraciones de fuente.

La salida es una fracción reducida con numerador/denominador enteros serializados como texto, evitando redondeo binario. Cero y cero con signo permanecen valor cero, con su representación original conservada. La longitud máxima es 256 caracteres de número como límite técnico. No se elige precisión financiera, redondeo ni tolerancia de aceptación.

La única escala implementada es porcentaje a fracción: un perfil de porcentaje exige unidad `%`, sufijo `%` en el literal y destino `fraction`; `5%` resulta exactamente 1/20. En notación decimal solo se permite identidad de unidad. No se anualizan montos, convierten monedas, cambian calendarios ni infieren factores de conversión. Un `5` con unidad `%` y perfil decimal conserva valor 5 en unidad `%`; no se divide automáticamente por cien.

## Metadatos y bloqueos

La unidad, moneda, período y referencia de definición de cada fuente deben coincidir exactamente con el perfil. Los perfiles monetarios requieren moneda explícita; los monetarios por período requieren además una identidad de período explícita y coincidente. Esta comprobación no certifica calendarios ni vigencia legal de un período: solo conserva y compara las declaraciones. La clasificación de cantidad tampoco valida por sí misma la definición económica del campo.

Bajo un perfil monetario USD, un literal con unidad `$` y moneda ausente queda bloqueado. El adaptador nativo T06 conserva justamente esa ausencia; el decodificador no la completa. Tampoco interpreta aliases de unidades ni transforma una referencia de mapeo en definición financiera adoptada. Los perfiles y fuentes deben aportar lo que afirman; no se crean declaraciones suplementarias para forzar coincidencia.

Faltantes y conflictos impiden convertir el campo. Si hay una declaración vacía junto con otra con valor, T07 bloquea hasta resolverlas; no selecciona el valor histórico. Dos representaciones distintas, aunque matemáticamente equivalentes como `0.10` y `0.1`, conservan el conflicto de fuentes sin política automática de reconciliación. Dos declaraciones coincidentes se conservan ambas y pueden decodificarse sintácticamente, sin autenticar ninguna.

## Ejecuciones y evidencia

`normalize_synthetic` devuelve un registro inmutable vinculado al snapshot exacto, su contexto, perfiles completos, hash de los perfiles, hash del código decodificador y declaraciones originales. Los campos admitidos reciben estado `decoded_synthetic`; el resto permanece `blocked`, con razones. `financially_validated=false`, `financially_normalized=false`, `run_ready=false` y `decision=PENDING` permanecen efectivos. No se cambian el borrador T01, los diez criterios vacíos ni las reglas del grafo T02.

`observe_normalization_freshness` compara fuente exacta, perfiles y versión del decodificador. Incluso un cambio de input no utilizado impide presentar la ejecución antigua como vigente para el nuevo snapshot. El informe solo observa identidad/vigencia, no certifica corrección financiera ni evita cambios posteriores; no autoriza publicación.

T03 incorpora `save_normalization` y `load_normalization`, reutilizando la tabla de objetos sin migración. Un paquete numérico conserva snapshot completo, perfiles, resultado, versión e inventario de fuentes. Captura y recuperación verifican fuentes/localizadores y reproducen la conversión. Cambiar un resultado y recalcular su hash no basta para superar la reproducción. La recuperación necesita la versión compatible del decodificador; los bytes siguen disponibles por hash aunque no sea posible reproducir con el código actual. Se usan APIs de carga distintas para paquetes numéricos y ejecuciones T02.

El hash no autentica personas ni hace resistente el sistema a un administrador que reescriba toda la evidencia. Las operaciones del archivo son transaccionales localmente; guardar una conversión no declara actual la cabecera del borrador ni implementa publicación atómica. Las bases runtime siguen fuera de GitHub y del ZIP documental.

## Ejemplo reproducible

Las plantillas `synthetic-normalization-source.json` y `synthetic-normalization-profiles.json` son datos/configuración ficticios, no valores activos del modelo. La demostración produce 1/20 desde `5%`, 21/400 desde `0,0525` y 1250 desde un monto con moneda/período explícitos. Otro monto con símbolo `$` sin moneda queda bloqueado bajo su perfil monetario. Ninguno representa un deal real o un umbral de aprobación.

Desde la raíz del repositorio, Python 3.11 o posterior:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python tools/demo_synthetic_normalization.py
```

Las 26 pruebas nuevas verifican exactitud decimal, coma declarada, porcentaje, cero, vacíos/conflictos, espacios, sintaxis no admitida, unidades/moneda/período/definiciones, contratos inválidos, ausencia de adopción de criterios, inmutabilidad, vigencia, hoja nativa sin moneda, reapertura del archivo, fraude de resultado con hash actualizado, fuente ausente, rollback y versión incompatible. Total técnico: 162 pruebas. Se mantienen aparte 26 suites de referencias, ocho fallos estructurales y 36 casos de aceptación financiera sin ejecución contra producto completo.

## Pendiente

Adopción trazable de definiciones financieras por campo, normalización completa de unidades/calendarios, integración de cálculos M2–M9, política de reconciliación de fuentes, comparaciones de inversión, revisión auténtica y publicación atómica. T07 sigue cubriendo parcialmente IMP-01/IMP-06; no cierra paquetes completos ni el modelo financiero. La próxima integración puede consumir estos números exactos solo bajo perfiles sintéticos explícitos y sin decisiones reales.
