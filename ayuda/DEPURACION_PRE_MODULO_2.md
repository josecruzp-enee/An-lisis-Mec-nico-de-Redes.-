# Auditoría de depuración previa al Módulo 2

Fecha: 2026-11-19. Rama: `main`.

## Criterio

No se eliminan algoritmos por su antigüedad o nombre. Se distinguen:
1. Archivos vacíos y código sin efecto, eliminables.
2. Copias byte a byte idénticas, consolidables manteniendo imports históricos.
3. Implementaciones diferentes y prototipos que pueden conservar dependencias; requieren revisión funcional antes de retirarse.
4. Pruebas y documentación de referencia, que se conservan para evitar regresiones.

## Cambios efectivos

- Eliminados `Ayuda/mapa_funciones.py` y `readme.md`, ambos vacíos.
- Eliminado un bucle sin efecto y una variable no usada en `resolver_seccion_deslizante_ideal.py`.
- Eliminada la importación `math` no utilizada en `generar_pdf_corrida_cfe.py`.
- Consolidados como rutas de compatibilidad, con implementación única en `analisis/calculos/`:
  `calculos/cargas_tramo.py`, `cimentacion.py`, `decision_soporte.py`,
  `equilibrio_poste.py`, `geometria.py`, `mecanica.py`,
  `momento_poste.py`, `perfil.py`, `retenidas.py`,
  `unidades.py`, `viento.py`.
- Consolidados como rutas de compatibilidad desde `analisis/entradas/` hacia `entradas/`: `catalogos.py`, `norma_postes.py`, `validacion_entrada.py`.
- Consolidado `analisis/exportacion_excel.py` hacia `salidas/exportacion_excel.py`.
- Añadidas pruebas `tests/test_compatibilidad_modulos_depurados.py`.

Estas consolidaciones preservan nombres y objetos importables mediante reexportación; el objetivo es eliminar implementaciones repetidas, no sus rutas públicas.

## Áreas que permanecen deliberadamente

- `calculos/engine.py` y `analisis/engine.py`: **no son copias exactas**. Hay diferencias en la integración de fuerzas; no unificar sin pruebas de los dos flujos y de la futura transición al Módulo 2.
- `calculos/fuerzas_nodo.py` y `analisis/calculos/fuerzas_nodo.py`: implementaciones de diferente alcance; no equivalentes.
- `salidas/reporte_pdf.py` y `analisis/reporte_pdf.py`: generadores históricos similares, pero no idénticos. Los reportes actuales del conductor se producen con `salidas/PDF/generar_pdf_corrida_cfe.py`. Auditar sus consumidores antes de retirar generadores históricos.
- `Analisis_mecanico_conductores/geometria/calcular_vanos_y_vano_regulador.py`: se importa desde `main.py`. El nombre heredado **no prueba que esté muerto**; el módulo de geometría requiere una decisión separada sobre el alcance del vano regulador.
- `app.py`: entrada real a Streamlit; no eliminar.
- `mapa_proyecto.py`: utilidad de análisis del repositorio, no parte del motor, pero puede ser usada manualmente.
- Pruebas, fixtures, catálogos CFE, PDF y documentación: conservados.

## Calidad y restricciones

- Mantener los valores de `alpha` inicial y final originales.
- No cambiar la física de catenaria, conservación de longitud ni las cinco hipótesis CFE como parte de una limpieza editorial.
- El caso de dos vanos desiguales y el caso individual de RAVEN forman parte de la regresión funcional esperada.
- Los tests automáticos están en `.github/workflows/pruebas_motor.yml`.
- Las regresiones pasan o fallan por commit concreto: verificar GitHub Actions para la versión que se quiera declarar estable. No asumir aprobación de un commit que no tenga aún CI concluida.

## Frontera para iniciar el Módulo 2

Entrada desde el Módulo 1: geometría XYZ y esfuerzos/reacciones por estado y por vano. El Módulo 2 debe producir:
- Demandas resultantes y momentos por apoyo y componente, sin confundir reacción del cable con capacidad.
- Comprobaciones resistentes de poste, cruceta, aislador, grapa, retenida y fundación, cada una respaldada por una tabla fuente.
- Casos gobernantes y utilización por elemento.
- Resumen de estados no evaluables por falta de propiedad documentada.
- Memoria y pruebas independientes del cálculo de conductores.

No activar como 'CUMPLE' los análisis preliminares de soporte existentes hasta verificar sus capacidades, combinaciones de carga, unidades y geometría.
