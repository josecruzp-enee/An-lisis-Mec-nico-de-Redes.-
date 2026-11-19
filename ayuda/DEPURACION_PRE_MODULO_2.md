# Auditoría y depuración previa al Módulo 2

**Fecha:** 19 de noviembre de 2026. **Rama:** `main`.

## Método utilizado

Se inspeccionaron todas las fuentes Python con un análisis estático reproducible en `tools/auditar_codigo.py` y se contrastaron las dependencias directas y transitivas con los puntos de entrada Streamlit y las pruebas. Se verificaron duplicados byte a byte, funciones equivalentes y módulos aislados. Una búsqueda sin referencias estáticas es un indicio, no una garantía absoluta de ausencia de uso externo.

La auditoría Ruff (`F401`, `F841`) identifica nombres que no se usan en cada archivo. Los reexports intencionales de los adaptadores pueden producir diagnósticos `F401`; **no deben eliminarse automáticamente**.

## Limpieza ejecutada

- Eliminados los dos archivos vacíos iniciales: `Ayuda/mapa_funciones.py` y `readme.md`.
- Simplificado el solucionador de guía deslizante y retiradas importaciones, variables o cálculos sin efecto en módulos activos.
- Unificadas quince copias exactas y tres implementaciones casi idénticas, eligiendo la implementación activa como canónica antes de retirar adaptadores sin consumidores.
- Eliminados los antiguos `analisis/engine.py`, `analisis/reporte_pdf.py`, `salidas/reporte_pdf.py`, `salidas/exportacion_excel.py`, `analisis/calculos/fuerzas_nodo.py` y rutas huérfanas de entradas.
- Eliminados los formularios CFE desconectados y adaptadores `calculos/` que no eran consumidos por la aplicación ni por las regresiones.
- En `main.py`, el resumen geométrico ahora usa `Analisis_mecanico_conductores/geometria/resumir_vanos.py`. Su cálculo no usa un vano regulador. Las referencias teóricas de Checa permanecen aisladas en su contexto correspondiente.
- Se mantienen las pruebas unitarias, los catálogos documentados CFE, la memoria PDF vigente, las funciones de cálculo activas y los módulos de soporte con consumidores.

## Verificaciones técnicas

La auditoría posterior a la eliminación de 20 módulos registró 214 fuentes Python y **cero duplicaciones de funciones equivalentes** según el detector AST. Una auditoría subsiguiente de dependencias identificó siete módulos aislados más, que también se retiraron, y finalmente un adaptador Excel adicional sin consumidores. Todas las ejecuciones de las regresiones deben juzgarse por el commit exacto que prueba GitHub Actions.

Las regresiones cubren funciones de conductor, tendido, catenaria, geometría, entradas y PDF. Las cinco hipótesis CFE y los coeficientes físicos originales no se alteraron como parte de esta depuración.

## Componentes que se mantienen por una razón

- `calculos/engine.py` es el motor preliminar de fuerzas con tensión prescrita que sigue siendo usado por `main.py`; no equivale al Módulo 2 completo.
- `calculos/fuerzas_nodo.py`, `calculos/modelo_red.py`, `calculos/ensamblador_global.py` y otros algoritmos 3D cuentan con consumidores. No se eliminan simplemente porque el flujo CFE no los invoque.
- `calculos/catenaria.py`, `calculos/cambio_estado.py` y otros adaptadores activos conservan contratos de importación y pruebas explícitas.
- `salidas/PDF/generar_pdf_corrida_cfe.py` genera la memoria de los análisis CFE. `salidas/PDF/generar_pdf_etapa_1.py` atiende el flujo general de Etapa 1.
- `app.py` es el punto de entrada de Streamlit y `mapa_proyecto.py` es una utilidad manual.
- `analisis/calculos/` conserva las funciones efectivamente importadas por el motor preliminar. Las implementaciones sin consumidores se retiraron.

## Verificación continua

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
python -m unittest discover -s Analisis_mecanico_conductores/pruebas -p 'test_*.py' -v
python tools/auditar_codigo.py
python -m compileall -q Analisis_mecanico_conductores analisis calculos entradas salidas main.py
```

El control de calidad impide importar módulos internos inexistentes. Las importaciones históricas activas se conservan de manera explícita, no duplicando la lógica.

## Alcance para Módulo 2

El Módulo 1 solo provee la respuesta mecánica calculada del conductor. La capacidad de poste, cruceta, aislador, grapa, retenida y cimentación requiere datos resistentes, combinaciones de carga y reglas de verificación independientes. Los resultados preliminares de los motores existentes **no son automáticamente diseños estructurales aprobados**.

Se deberá verificar por hipótesis la demanda XYZ y momentos, los límites documentados por componente, el porcentaje de utilización y la trazabilidad completa en PDF, con `NO VERIFICABLE` cuando falten datos.
