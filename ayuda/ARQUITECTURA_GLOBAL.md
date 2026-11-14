# Arquitectura del cálculo mecánico global

**Estado: motor de desarrollo, NO dimensionamiento.** El programa histórico de
Streamlit sigue usando su propio cálculo preliminar. Los nuevos módulos no se
re-etiquetan como "modelo completo" antes de integrar los elementos faltantes.

## Método de solución

La red se representa como un grafo de apoyos, amarres y vanos. El modelo
distingue el tipo de conexión en **cada extremo de cada vano**. En el futuro,
un mismo apoyo podrá tener un circuito en remate y otro en suspensión.

Para un vano de cable flexible en coordenada material `s`:

`dr/ds = (1+|T|/EA) T/|T|`

`dT/ds = -(1+|T|/EA) (q_gravedad + q_viento(T/|T|))`

El viento se proyecta respecto a la tangente local `T/|T|`, no respecto al
eje recto del vano. La compatibilidad térmica se impone conservando la
longitud natural del tendido `S0` durante el movimiento de los apoyos.

El equilibrio de los nodos trasladables con matriz de rigidez K definida
positiva es:

`R_i(u) = sum(F_cables_i(u)) + F_adicionales_i - K_i u_i = 0`

El solucionador global utiliza `scipy.optimize.least_squares` con re-evaluación
de cada problema de contorno mediante `solve_bvp`. Valida residuales físicos
y rechaza la falta de convergencia. La rigidez debe venir con una fuente.

**No significa que la ingeniería del sistema esté completa**. Esta fase
sólo admite conexiones fijas/retenidas y apoyos fijos o trasladables con
rigidez 3x3. Aún falta formular y acoplar al sistema:
- Suspensiones con movilidad del conductor, cadenas finitas y fricción.
- Seis grados de libertad de postes, geometría deformada y flexión/axial.
- Ley unilateral de retenidas (sin compresión), pretensado y anclajes.
- Interacción suelo–cimentación e incertidumbre geotécnica.
- Materiales ACSR multicapa específicos y curvas de fluencia / plasticidad.
- Herrajes, aisladores, viento del propio poste, peso y acciones térmicas
  adicionales en el **mismo** ensamblador; hoy sólo se pueden suministrar
  como fuerzas nodales externas conocidas.
- Malla topográfica densa, vegetación, obstáculos, despejes eléctricos y
  condiciones normativas de resistencia y servicio.
- Modelos de viento turbulento/dinámico si corresponden al estado de diseño.

No se crearán "equilibrios globales" ficticios por asignar a toda suspensión
la condición de anclaje. Los casos no soportados fallan explícitamente.

## Excel explícito para redes

El antiguo Excel de una sola hoja sigue siendo válido para el módulo
preliminar, pero **no contiene la conectividad mecánica suficiente** para una
red real. Para un proyecto con ramales, remates y múltiples circuitos:

### Hoja `Puntos`

`Punto | X | Y | Altitud | Poste | Fijacion`

- `X,Y,Altitud`: coordenadas m referidas al mismo sistema.
- `Fijacion`: `FIJO` o `MOVIL`, según el modelo mecánico suministrado.
- `Poste`: identificación de catálogo, no capacidad por sí sola.

### Hoja `Vanos`

`Vano | Inicio | Fin | Circuito | Seccion | Conductor | Conexion_Inicio | Conexion_Fin | Altura_Inicio_m | Altura_Fin_m`

- `Inicio,Fin`: identificadores de apoyo.
- `Circuito,Seccion`: identificadores explícitos de trazabilidad.
- `Conexion_Inicio/Fin`: `ANCLAJE`, `FIJA`, `SUSPENSION` o `DESLIZANTE`.
- Alturas de amarre en metros sobre terreno de cada apoyo.
- En topología, las secciones son cadenas conectadas entre anclajes: no
  se usan fórmulas equivalentes de vano regulador como sustituto de
  compatibilidad y equilibrio.

La función `entradas.importar_red.leer_red_excel` construye el grafo.
En proyectos reales harán falta además coordenadas XYZ **por fase**,
dispositivos de acople, características mecánicas y leyes de material.

## Archivos

- `calculos/modelo_red.py`: grafo y validación de secciones.
- `entradas/importar_red.py`: entrada Excel multicircuito explícita.
- `calculos/cable_no_lineal.py`: problema de contorno de un cable.
- `calculos/ensamblador_global.py`: equilibrio nodal acoplado en
  traslación, referencias indeformadas y residuales.
- `tests/test_modelo_red.py`, `tests/test_importar_red.py`,
  `tests/test_ensamblador_global.py`: regresión numérica y de contrato.

El cálculo final sólo podrá declararse utilizable en diseño cuando el
dominio de aplicación, la calidad de entrada y las verificaciones de
material, componentes y suelo estén respaldados y trazados.
