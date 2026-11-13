# Auditoría técnica inicial del motor de cálculo

> Las salidas actuales son **preliminares** y no deben utilizarse por sí solas como aprobación de una estructura para construcción.

## Cambios incorporados en esta rama

- El poste desconocido deja de recibir una resistencia ficticia de 9999 kN.
- La alternativa **autosoportada** deja de considerarse automáticamente válida al faltar espacio para retenidas.
- La selección de retenida considera explícitamente el indicador de cumplimiento de su capacidad.
- El evaluador de decisiones ya no modifica los DataFrames de entrada durante la normalización de identificadores.
- Se agregan casos de regresión para evitar repetir estas decisiones peligrosas.

## Bloqueantes del modelo físico pendientes de resolver

1. **Tensión longitudinal:** `fuerzas_nodo.py` distribuye cargas por viento, pero todavía no incorpora las resultantes vectoriales de la tensión de los conductores en cambios de dirección y remates. No debe interpretarse `H (kN)` como la solicitación total de diseño.
2. **Combinación vertical/horizontal:** `engine.py` utiliza `w_resultante (kN/m)` para fuerzas nodales en planta; esto incluye el peso vertical y puede convertirlo erróneamente en fuerza horizontal.
3. **Alturas y enterramiento:** `perfil.py` calcula el amarre usando la longitud total sin descontar el enterramiento; `norma_postes.py` tiene la misma limitación. Regla de enterramiento definida para postes en pies: `d_ft = 0.1 * longitud_ft + 2`. Falta implementar de forma consistente en todas las etapas, sin mezclar unidades.
4. **Perfil longitudinal:** la catenaria utilizada calcula una flecha nivelada pero representa el perfil con una parábola incluso en desniveles de apoyo. Deben diferenciarse modelo exacto, aproximación y supuestos.
5. **Cimentación:** `cimentacion.py` adopta `R = M/d` como fuerza equivalente y `engine.py` fija `d=2.0 m` y `capacidad=50 kN` sin datos geotécnicos. Esto no constituye comprobación de resistencia de suelo.
6. **Resistencia del poste:** `norma_postes.py` usa directamente carga de ruptura como `H_max` para ciertos registros. Se necesitan resistencia admisible/de diseño, referencia de ensayo, brazo de carga y factores aplicables.
7. **Retenidas:** verificar vector de orientación, resistencia de anclaje, capacidad del cable y efectos verticales sobre poste/cimentación.
8. **Normativa:** registrar versión, fuente y ámbito de aplicación de los catálogos; comprobar hipótesis de viento, combinaciones y seguridad.

## Orden sugerido de continuación

1. Definir contrato de unidades, entradas y supuestos.
2. Implementar tensión por conductor y equilibrio vectorial en cada nodo.
3. Corregir alturas de amarre, enterramientos y perfiles.
4. Agregar verificaciones de resistencia de poste, retenida, anclaje y cimentación.
5. Validar manualmente ejemplos rectos, ángulos, remates y alturas variables.
6. Solo entonces habilitar dictámenes de cumplimiento y reportes de diseño.

La primera modificación de esta rama **no corrige aún el modelo físico**; evita que ciertas decisiones sin respaldo se presenten como soluciones verificadas.
