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
9. Momento por producto vectorial brazo-amarrre x fuerza para cada poste.
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
- Validación de referencia adicional (casos benchmark por desnivel,
  vanos largos, convergencia de malla, estudios de sensibilidad).
- Optimización computacional y seguimiento de cálculo en redes extensas.

## Archivos vigentes

- `calculos/cable_no_lineal.py` — problema de contorno.
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
