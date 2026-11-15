# Módulo 01 — Diseño inverso de tensión de tendido

## Referencias documentales del proyecto

1. Luis María Checa, *Líneas de Transporte de Energía*, 3.ª edición,
   capítulo 4 «Cálculo mecánico de cables»: equilibrio de hilo suspendido
   y ecuación de cambio de condiciones, especialmente pp. impresas
   217–221 y 238–243 (ejemplar PDF compartido por el proyectista).
2. *Cálculo mecánica de conductores aéreos*, resumen ISEP entregado,
   pp. 2–6: selección del estado base, hipótesis climáticas, ecuación
   de estado, vano crítico y tabla de tendido.
3. Viakon, *Manual del Electricista* (2020), catálogo ACSR para masas,
   diámetros y cargas de ruptura nominales.
4. Nexans, características finales E/alpha según construcción ACSR,
   **solo para análisis comparativos**, no como certificación Viakon.

## Fórmulas de referencia, no sustitutos del motor 3D

En el resumen ISEP, para vanos con pequeñas pendientes y flechas,
se emplean las aproximaciones parabólicas de flecha y longitud:

- `f ≈ g*a²/(8*P)`
- `L ≈ a + g²*a³/(24*P²)`

Su ecuación de cambio de estado relaciona deformación elástica y
dilatación térmica entre dos hipótesis climáticas; el vano crítico
sirve para reconocer cuál régimen puede gobernar en la aproximación.

La **solución operativa** en `calculos/tendido_inverso.py` no depende
de esas simplificaciones: cada hipótesis se evalúa con
`resolver_cable_no_lineal`, un problema de contorno espacial que
conserva longitud natural y aplica viento normal a la tangente local.

## Función implementada

`dimensionar_tension_tendido` recibe:

- Geometría XYZ de un **único vano con amarres fijos**.
- Peso por metro, diámetro, EA, alpha, fuente y temperatura de tendido.
- Hipótesis climáticas individuales: temperatura, velocidad de viento,
  azimut, límite de tensión **en kN**, criterio y fuente de límite.
- Un intervalo EXPLÍCITO de búsqueda de H y temperaturas de la tabla.

Entrega:

- H de referencia seleccionada dentro del intervalo indicado.
- T máxima, razón T/límite y estado por hipótesis.
- Hipótesis gobernante, razón máxima y condición de borde activo.
- Tabla de tendido para cada temperatura sin viento con tensiones en
  ambos extremos, tensión máxima, flecha vertical respecto a la cuerda,
  longitud y residual.
- Evaluaciones de BVP efectuadas.

Se selecciona la **mayor tensión de tendido que satisface las hipótesis
de tracción especificadas** dentro del intervalo. La monotonía se
comprueba mediante muestras y se rechaza una tendencia no monótona
detectada. Esta verificación de muestra NO constituye una prueba
matemática global de monotonía; por ello su uso se limita al intervalo
ensayado y a las hipótesis verificadas.

## Límites explícitos

**No es una aprobación automática de una línea eléctrica.** Falta:

- Clasificación normativa aprobada de estados climáticos de Honduras
  y coeficientes/límites de diseño particulares de cada emplazamiento.
- Modelo constitutivo ACSR inicial/final, fluencia dependiente del
  tiempo y temperatura y validación por fabricante específico.
- Despejes contra topografía y obstáculos reales, vibraciones y fatiga.
- Continuidad y redistribución entre vanos con grapas de suspensión,
  poleas, amarres, cadenas, retenidas y movimiento de postes.
- Probar la unicidad/monotonía o emplear algoritmo global probado si
  la relación tensión-tendido deja de ser monótona.
- Dimensionamiento estructural, apoyos y fundaciones.

**No asignar automáticamente porcentajes de ruptura** como tensión de
diseño. El documento de clase debe provenir del proyecto y su fuente
debe estar identificada. El documento ISEP no es una norma hondureña.

## Estado y pruebas

Implementación: terminada para el alcance declarado de un vano fijo
con elasticidad lineal y límites documentados.

Validación de software: pruebas en
`tests/test_tendido_inverso.py`: factibilidad, tabla de tensiones y
flechas, límite superior activo, rechazo de hipótesis imposibles,
rechazo de parámetros sin fuente y detección de monotonía adversa.

**El Módulo 01 global de redes reales no está todavía cerrado.**
