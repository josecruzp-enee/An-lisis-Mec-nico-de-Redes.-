# Migración modular y depuración antes del Módulo 2

**19 de noviembre de 2026 — rama `main`.**

## Decisión de arquitectura

`main.py` presenta la interfaz; `motor_general.py` coordina la ejecución. Cada módulo contiene sus propias entradas, algoritmos y salidas. Las carpetas `Analisis_mecanico_conductores/` y `Analisis_mecanico_estructuras/` no deben importarse entre sí; se comunican únicamente a través del coordinador.

## Cambios completados

1. Auditoría estática de archivos Python, importaciones, dependencias transitivas y duplicaciones, automatizada en `tools/auditar_codigo.py`.
2. Consolidación y eliminación de archivos vacíos, adaptadores sin consumidores y variables sin efecto, manteniendo los cálculos con utilidad técnica.
3. Migración **sin modificación de ecuaciones** de las once implementaciones de `analisis/calculos/` a `Analisis_mecanico_estructuras/calculos/`: cargas por tramo, cimentación, decisión de soporte, equilibrio, geometría, mecánica, momento de poste, perfil, retenidas, unidades y viento.
4. Migración de `calculos/fuerzas_nodo.py` a Módulo 2, de `entradas/norma_postes.py` a `Analisis_mecanico_estructuras/entradas/` y de `calculos/engine.py` a `Analisis_mecanico_estructuras/motor.py`.
5. Introducción de `motor_general.py` y migración de llamadas de cálculo, geometría y generación PDF desde la interfaz a este coordinador.
6. Traslado de los ocho archivos PDF de `salidas/PDF/` a `Analisis_mecanico_conductores/salidas/PDF/`. Los informes CFE y del módulo general conservan su lógica de generación.
7. Traslado del catálogo Viakon ACSR a `comun/catalogo_acsr_viakon.py`; las antiguas rutas públicas del Módulo 1 y `entradas/` reexportan la **misma** tabla física, sin duplicarla.
8. Eliminación de las carpetas históricas `analisis/` y `salidas/` después de actualizar sus consumidores; conservación del directorio `calculos/` para algoritmos globales todavía utilizados.
9. Pruebas de equivalencia entre el antiguo motor de estructuras y el nuevo motor; pruebas de invariancia del catálogo y de ausencia de importaciones cruzadas.

## Qué NO constituye la migración

No se han calculado automáticamente capacidades resistentes nuevas de poste, cruceta, aisladores, anclajes o cimentaciones. Las rutinas anteriores de estructuras se mantienen con su alcance histórico; sus resultados preliminares no autorizan declarar `CUMPLE` si faltan propiedades.

No se modificaron coeficientes `alpha`, ecuaciones de catenaria 3D, compatibilidad termoelástica, hipótesis CFE o selección de casos mecánicos. El conjunto de pruebas se ejecuta por commit en GitHub Actions; revisar la última ejecución antes de declarar la versión estable.

## Preparación del Módulo 2

El siguiente desarrollo deberá tomar esfuerzos XYZ y momentos del Módulo 1 mediante un **contrato explícito de resultados** definido en el motor general. Verificará por elemento las demandas frente a capacidades documentadas, sin recurrir a parámetros ficticios, y generará una memoria propia.
