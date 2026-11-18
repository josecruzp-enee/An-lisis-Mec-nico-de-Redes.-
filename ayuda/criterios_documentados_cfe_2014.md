# Extracción y verificaciones CFE 2014 — conductor, estructura y libramientos

Fuente primaria: `Manual_lineas.pdf` (CFE, construcción de instalaciones aéreas de media y baja tensión, 2014).
**Esta referencia no sustituye un manual ni capacidades ENEE para una obra en Honduras.**

## Catálogos incorporados

- `entradas/catalogos/cfe_limitantes_estructuras_120kmh.csv`: **662 filas** documentales de 17 combinaciones estructura/ambiente; 13 conductores y clases 13/23/33 kV; columnas separadas de poste, cable, perno, perno punta poste donde aplica, cruceta con/sin hielo, piso, fases, deflexión y desnivel. Secciones 05 T0 02 (PDF 181–184), 05 T0 09 (210–213), 05 P0 02 (241–242), 05 P0 05 (256–257), 05 R0 02 (273), 05 V0 02 (409–412).
- `entradas/catalogos/cfe_limitantes_estructuras_H_120kmh.csv`: **27 filas** HS3G y HA3G, con tensiones, claros medio horizontal y vertical y parámetros CFE; sección 05 H0 02 (PDF 496–497).

**Advertencias de extracción:**
1. No está publicada en la página 410 una fila VD3N normal, HAWK, 33 kV; se deja ausente.
2. En 05 R0 02, la página 272 indica adoptar límites TS para remate, pero la tabla de la página 273 está encabezada PS3N. Se preserva como `R/PS3N` sin resolver la contradicción.
3. Cada cifra conserva página; ninguna es una capacidad mecánica intrínseca independiente de la estructura postulada por CFE.
4. El viento de referencia tabular es 120 km/h, con los postes y crucetas CFE descritos en cada sección. No trasladar estos límites a A-III-1, A-III-2 u otras estructuras ENEE por semejanza de función.

## Requisito 1 — tracción máxima del conductor

CFE 05 00 03, PDF p156, establece:
- final 16 °C sin viento: 20 % RTS;
- final 0 °C sin viento: 25 % RTS;
- inicial 0 °C sin viento: 33 % RTS;
- final −10 °C con viento reducido y hielo: 45 % RTS;
- final 0 °C con viento máximo: 45 % RTS.

Debe compararse **tensión máxima resultante por vano y por estado**, no solamente H horizontal. El motor debe informar `NO VERIFICABLE` si falta un caso o una ley constitutiva inicial/final justificable.

## Requisito 2 — límites de elementos CFE

Consultar la fila exacta `(estructura, ambiente, conductor, clase de tensión)`. Verificar individualmente máximos de poste, cable, perno, cruceta, piso, fase, deflexión y desnivel. No confundir el claro interpostal con el claro regulador o con el claro medio horizontal de una estructura H. Para redes ENEE se requieren capacidades reales documentadas de los componentes instalados.

## Requisito 3 — geometría, fases y obstáculos

- CFE 02 00 03 (PDF p43–44): alturas mínimas según superficie, con flecha **final a 50 °C, sin viento**. En línea abierta MT: 7 m sobre carreteras/calles; 6 m a lo largo de caminos y zonas rurales; otros cruces tienen mínimos propios. Suelo plano por sí solo no identifica la superficie.
- CFE 02 00 04 (PDF p45–46): separación horizontal a construcciones con conductor desplazado por viento, **16 °C final**. La página 45 imprime `19 kg/m` como presión, lo que es dimensionalmente ambiguo; **no sustituir sin justificación por kgf/m²**. La categoría de línea abierta de 750 V a 23 kV presenta 2.30 m horizontales; a 33 kV, 2.50 m.
- CFE 02 00 06 (PDF p47–49): separación de fases entre apoyos; para flechas mayores de 60 cm tabula 60–300 cm. Por encima de 300 cm no extrapolar ni declarar cumplimiento. La separación mínima entre fases exige posiciones y oscilaciones reales, no solo flecha.
- Evaluar verticales, horizontales y distancias mínimas por vano contra geometría del terreno/construcciones y disposición de fases. Ausencia de un dato: `NO VERIFICABLE`.

## Prueba de regresión catenaria RAVEN

`tests/fixtures/validacion_catenaria_CFE_RAVEN_50C.csv` conserva 21 filas publicadas en CFE 07 FT 10, PDF p609. Con el P publicado empleado **solo en la prueba**, y `w=2.12 N/m`, se verifican las identidades `H=w*P` y `f=P*(cosh(L/(2P))-1)`.
Máximas diferencias por redondeo/tabulación: 0.51 kgf en H, 0.70 cm en flecha. Esto **no verifica** el método de obtención de P, cambio de estado, creep ni compatibilidad multivano.

## Integración

- `Analisis_mecanico_conductores/verificaciones/verificar_restricciones_documentadas_cfe.py`: comprobadores puros, sin modificar soluciones mecánicas.
- `Analisis_mecanico_conductores/verificaciones/evaluar_requisitos_cfe_por_vano.py`: liga tablas y geometría explícitamente documentada a `resultado.flechas`.
- `ejecutar_analisis_integral(..., configuracion_cfe=...)`: opt-in; el solver histórico no cambia. Los valores no proporcionados quedan `NO VERIFICABLE`.
- Pruebas en `tests/test_restricciones_cfe_documentadas.py` y `tests/test_regresion_catenaria_cfe_raven_50C.py`.

**No se ha acreditado aún el cálculo completo de tensión de tendido inicial/final ni una solución constructiva ENEE. Ningún resultado provisional de los 5 vanos debe presentarse como diseño aprobado.**
