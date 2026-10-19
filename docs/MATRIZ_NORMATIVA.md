# Matriz normativa y datos pendientes

La bibliografía indicada en el prompt no está incorporada al repositorio.
Esta implementación no afirma haber verificado cláusulas ni páginas de esos PDF.
No se confunde una referencia bibliográfica con una norma obligatoria ENEE.

| Control | Referencia a revisar | Información indispensable | Estado |
|---|---|---|---|
| Estructuras, construcción y amarres | Manual de Obras ENEE, versión aplicable | Lámina, dimensiones, alcance y aprobación | Pendiente |
| Poste concreto | Especificación ENEE concreta y ficha fabricante | Ruptura/prueba/servicio, altura de ensayo, sección y material | Sólo ruptura en catálogo; insuficiente |
| Poste madera | Especificación ENEE, clase y especie | Geometría, especie, resistencia, condición y degradación | Pendiente; PM no se asimila a PC |
| Poste metal/PRFV | Anexo 14 y ficha real | Sección, rigidez, estabilidad y conexiones | Pendiente |
| Conductor ACSR 477 | Fabricante del cable exacto | Composición, EA, alpha, RTS, curva tensión-deformación, creep | Catálogo parcial; Flicker no verificado |
| Clima y combinaciones | NESC/IEEE C2, IEC 60826 según alcance | Edición, grado/clase, ubicación, factores y periodos | Parámetros explícitos; sin selección normativa |
| Metodología de cargas | ASCE 74, edición aplicable | Hipótesis y método compatible | Complementaria; no mandato ENEE |
| Libramientos | Manual ENEE y NESC según proyecto | Tensión, cruce/uso del terreno, temperatura, edición | Sin límite por defecto |
| Retenidas/herrajes | Norma ENEE y fabricante | EHS real, FS o factor, dirección y geometría, conexiones | Sin aprobación automática |
| Ancla y suelo | Estudio geotécnico y método adoptado | Estratos, nivel freático, rigidez lateral, extracción | NO VERIFICABLE sin modelo/datos |
| Catenaria y cambio de estado | Checa, Kiessling, CFE como bibliografía | Comparación de ejemplos y localización de ecuaciones | Implementación deducida y pruebas; cita pendiente |

Jerarquía: ENEE oficial → especificaciones ENEE → normas complementarias
aplicables → fundamentos matemáticos → hipótesis declaradas. Si hay conflicto,
registrar resolución técnica antes de adoptar un criterio. El usuario aporta
fuentes; el software verifica presencia/compatibilidad, no autenticidad de texto.
