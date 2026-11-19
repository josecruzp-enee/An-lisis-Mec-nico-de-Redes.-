# Auditoría técnica y arquitectónica — 19 de noviembre de 2026

## Alcance y línea de base

Rama `main`, commit inicial `248f8401d7697c039a2ab30db001c4cf4fccee1b`.
Inventario comprobado: **161 archivos**, de los cuales **149 Python**.
El auditor automático en GitHub Actions examinó **656 definiciones de función** y **319 relaciones de importación**.
La ejecución de la suite precedente terminó correctamente.

## Conclusión de depuración

La evidencia **no autoriza una eliminación masiva** sin perder capacidades.
El programa no tiene 161 implementaciones duplicadas: contiene fuentes, catálogos, pruebas,
interfaz, documentación y varios modelos físicos independientes.
El análisis estático no encontró errores sintácticos ni importaciones internas inexistentes
y no identificó funciones idénticas de longitud significativa en archivos distintos.
Las únicas copias exactas reportadas fueron tres `__init__.py` vacíos del Módulo 2;
son marcadores de paquete y conservarlos es apropiado.

## Arquitectura y dependencias corregidas

1. `Analisis_mecanico_conductores/entradas/leer_tension_inversa_desde_excel_historico.py`
   importaba un parser ubicado en `interfaz/mostrar_tendido_inverso_un_vano.py`.
   Se extrajo ese parser **sin cambiar la validación ni el tipo de salida** a
   `entradas/hipotesis_tendido.py`; la interfaz conserva sus nombres públicos
   mediante importación desde el módulo de entrada.
2. `Analisis_mecanico_conductores/entradas/leer_datos_y_calcular_regulacion.py`
   invocaba `motor_general.ejecutar_modulo("conductores", ...)` y creaba una dependencia
   de retorno desde el módulo a su coordinador superior. Ahora llama directamente
   a la **misma** implementación `ejecutar_analisis_integral` del propio Módulo 1.
   No hay cambio de parámetros, fórmulas, criterios ni salida.
3. Se actualizó el contrato de pruebas para impedir importaciones desde la capa
   `entradas/` del Módulo 1 a `interfaz/` o `motor_general`.
4. Se corrigieron rutas obsoletas de `README.md`, del README del Módulo 1 y del
   flujo de GitHub Actions (la carpeta histórica raíz `calculos/` ya no existe).

## Revisión del Módulo 1

Se conservaron expresamente las implementaciones independientes de catenaria
analítica y BVP tridimensional, cambio de estado, estados climáticos, CFE,
cálculo inverso, vanos amarrados, sección deslizante ideal, red global, barrido
global, verificaciones, PDF, interfaz y propiedades documentadas.
`barrido_global.py` está cubierto por pruebas, aunque no se invoque desde
la pantalla principal: **no es código descartable**.
`cfe_claro_diseno_y_claros_regla.py` y
`verificar_limites_documentados_de_tension.py` tienen uso comprobado
en pruebas y preservan funcionalidad de referencia.

## Revisión del Módulo 2

Se mantuvieron todos los cálculos preliminares de geometría, cargas,
postes, retenidas, cimentación, resistencias y perfiles. El módulo no debe
confundirse con una certificación completa de diseño mecánico.
`salidas/resultados.py` es un adaptador de exportación no alcanzado por la
interfaz ni las pruebas actuales. Es pequeño y proporciona una salida pública
del Módulo 2; se **conserva** como avance para reportes futuros.
Las importaciones de utilidad desde `motor_general.py` son una API pública
utilizada por vistas y ensayos y no deben borrarse solo porque un linter marque
símbolos reexportados como aparentemente sin uso.

## Riesgos y pendientes

- La inspección estática **no detecta** todas las llamadas dinámicas ni compara
  exhaustivamente equivalencia numérica.
- El programa tiene varias entradas y rutas de compatibilidad heredadas; eliminarlas
  exigiría identificar los consumidores reales fuera del repositorio.
- Es importante mantener las regresiones de las tablas CFE, las hipótesis físicas
  y los casos de convergencia. Una reducción adicional de archivos no es un
  objetivo técnico por sí misma.
- Quedan pendientes las capacidades estructurales certificadas y verificaciones
  integrales del Módulo 2. No se alteran esas áreas durante la auditoría.

## Criterios de aceptación

Se exige que las pruebas de regresión, auditoría estructural y compilación
sintáctica sigan aprobando en GitHub Actions tras aplicar estos ajustes.
No se modificaron intencionalmente ecuaciones, coeficientes ni tolerancias
de convergencia. Esta revisión **no afirma una nueva validación física**.
