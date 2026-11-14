# Módulo 01 — Análisis mecánico de conductores

**Estado: integrado en el barrido 3D de Streamlit, validación en curso.**
No declarar COMPLETADO para una RED REAL hasta cerrar las pruebas y el
dominio de conexión física indicados abajo.

## Objetivo y contrato

Para cada vano con extremos **realmente fijos** y sus condiciones de
tendido, resolver un problema de contorno no lineal en 3D del conductor
flexible extensible, con gravedad, viento constante en el espacio y
arrastre normal a la tangente local de la curva.

El usuario selecciona conductor, tensión de tendido, velocidad de viento,
temperaturas y geometría desde Excel. Peso y diámetro proceden del catálogo;
EA y dilatación deben tener fuente técnica, de lo contrario el programa
opera con parámetros sintéticos y alerta **NO APTO PARA DISEÑO**.

No se inventan continuidad entre vanos, rigidez, pretensiones ni datos de
topografía. La pantalla existente del barrido emplea amarres fijos aunque
reciba tres o más postes. La conectividad real de suspensiones se estudiará
con el ensamblador global y sus leyes de unión.

## Fuentes externas incorporadas (control de ingeniería)

**Viakon — Manual del Electricista, junio de 2020, pp. 18–20:**
tabla ACSR por **calibre + nombre del ave** (p.ej. 2/0 QUAIL, 477
HAWK/FLICKER), construcción de alambres, diámetros, peso por longitud,
carga nominal de ruptura y resistencia eléctrica.
https://viakon.com/wp-content/uploads/2020/11/ManualElectricista_2020.pdf

**Nexans — T-ACSR Cable Stress and Strain Characteristics:** tabla
de E inicial/final y alfa inicial/final por **construcción Al/acero**.
https://www.nexans.com.br/.rest/eservice/dam/v1/file/223724/StressStrainACSR_es.pdf

**Trefinasa — Overhead Conductors, ACSR:** fuente externa secundaria
para contraste de módulo final y coeficiente de expansión por
configuración 6+1, 6+7 y 26+7.
https://www.trefinasa.com/wp-content/uploads/2017/04/overhead_conductors_trefinasa_2016web.pdf

La tabla Nexans es de **otro fabricante**. No transforma una ficha
Viakon en ficha certificada de elasticidad y creep. El modo opcional
de referencia utiliza E_final, α_final y área metálica total calculada
de los alambres para un **estudio comparativo no apto para diseño**.
En particular, el modelo actual sigue siendo una elasticidad axial
lineal; no reproduce automáticamente el cambio de módulo durante
el tendido y las curvas de tensión-deformación completas.

**Control mecánico automático:** se evalúa para cada caso
`T_max / T_ruptura_nominal`. Igualar o superar 1 detecta demanda
compatible con rotura nominal; un valor menor **NO significa CUMPLE**,
pues aún faltan los límites de servicio EDS/EDA/condiciones de diseño
y los coeficientes aplicables.

## Cálculos implementados

1. Geometría 3D de cada vano y desniveles entre amarres.
2. Referencia de tendido sin viento, con tensión horizontal inicial.
3. Longitud natural recuperada por compatibilidad elástica.
4. Expansión térmica conservando longitud natural de referencia.
5. Ecuación diferencial de equilibrio y arrastre normal a tangente local.
6. Tensión y fuerzas XYZ en ambos amarres y máxima tensión a lo largo del cable.
7. Geometría espacial: flecha vertical relativa a cuerda y desviación lateral.
8. Despeje frente a terreno **lineal interpolado**: solo referencia,
   nunca certificación de libramientos en montaña o frente a obstáculos.
9. Momento por producto vectorial brazo-amarre x fuerza para cada poste.
10. Auditoría por extremo de vano: suma completa Fx,Fy,Fz,Mx,My,Mz.
11. Envolventes que preservan caso físico: tensión máxima, flecha,
    mínimo despeje de referencia y fuerzas de cada poste.
12. Rechazo explícito de la falta de convergencia de BVP y de
    desequilibrios fuera de tolerancia.

## Verificación automática

- Solución de la catenaria sin viento como referencia analítica.
- Condición de extremos y residual de fuerzas para viento oblicuo.
- Cambio de estado con temperatura distinta a la del tendido.
- Geometría de flecha contra muestreo numérico independiente.
- Conservación de las seis componentes al acumular cargas por apoyo.
- Envolventes preservando el caso gobernante y unidades correctas.
- Entradas de dominio y errores sin reemplazarlas por ceros.
- Suite de regresión de GitHub Actions.

**Las pruebas de software NO certifican el comportamiento del conductor
real**, porque sigue faltando validación experimental/independiente de los
parámetros materiales y de los casos de diseño aplicables.

## Pendiente para cerrar el Módulo 01 en redes reales

- Materiales ACSR: fichas verificadas, rigidez efectiva, expansión,
  tensiones admisibles, historia térmica y creep documentados por modelo.
- Topología real de las conexiones y repartición entre vanos en las
  suspensiones apropiadas, sin tratarlas por defecto como amarres fijos.
- Perfil de terreno verificado e inclusión de obstáculos y criterios de
  libramiento en un módulo especializado.
- Casos físicos adicionales según proyecto: hielo, cambios de sección,
  concentraciones en herrajes, límites de viento y efectos dinámicos.
- Ampliar la validación de referencia (los benchmarks de vano
  de 225 m, 68 m de desnivel, viento oblicuo y doble malla YA ESTÁN
  implementados y pasan). Quedan por contrastar casos medidos,
  series de estados térmicos y múltiples configuraciones materiales.
- Optimización computacional y seguimiento de cálculo en redes extensas.

## Mejoras de ingeniería y rendimiento incorporadas

- Tensión máxima del conductor calculada por búsqueda sobre el
  interpolador continuo del BVP, no solo sobre una tabla de 150 puntos.
- Optimización de estado SIN VIENTO: reutiliza un BVP entre azimuts,
  conservando las filas y casos de salida para trazabilidad.
- Comparación por caso de `T_max/T_ruptura`, con interrupción de
  verificaciones posteriores cuando se alcanza/supera la carga nominal
  de ruptura. Esta barrera NO sustituye un factor de seguridad.
- Catálogo Viakon de múltiples construcciones por ave; control de
  coherencia del área de aluminio `N*pi*d²/4` contra la sección
  nominal declarada.
- Catálogo heredado de Fase 1 mapeado a las mismas fichas Viakon,
  sin dos listas independientes de peso y ruptura.
- Tabla de catálogo visible y exportable en CSV desde Streamlit,
  separando fuentes nominales de referencias mecánicas.
- Ensayos CI de dispersión por temperatura/viento, conservación de
  cargas por extremos, interpolador BVP y documentación de fuentes.

**Limitación:** la ausencia de datos certificado de fabricante para
curvas completas tensión-deformación, creep y estado inicial/final
continúa impidiendo declarar completo el Módulo 01 para diseño de red
real. Ningún resultado de sensibilidad Nexans debe imprimirse como
cálculo certificado Viakon.

## Archivos vigentes

- `calculos/cable_no_lineal.py` — problema de contorno.
- `entradas/catalogo_viakon_acsr.py` — datos nominales Viakon por ave.
- `entradas/referencias_mecanicas_acsr.py` — E/alpha finales Nexans por configuración, solo comparación.
- `calculos/diagnostico_tension_acsr.py` — cribado T_max/ruptura por caso.
- `entradas/tabla_catalogo_acsr.py` — exportación y contraste de fuentes.
- `calculos/barrido_no_lineal_3d.py` — barridos y resultados por vano.
- `calculos/cambio_estado.py` — referencia de compatibilidad.
- `calculos/auditoria_cargas.py` — trazabilidad de cargas.
- `calculos/envolventes_3d.py` — casos gobernantes.
- `entradas/interfaz_barrido_3d.py` — pantalla de cálculo.
- `calculos/barrido_3d.py` — método anterior conservado para pruebas
  comparativas, **no es el motor principal de esta pantalla**.

El Módulo 02 recibirá fuerzas XYZ y momentos por extremo, sin sustituir
el detalle de fases por una resultante única cuando tengan alturas
y brazos diferentes.
