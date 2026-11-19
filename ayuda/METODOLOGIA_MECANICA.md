# Metodología mecánica, modelos de referencia y límites

**Documento único de metodología** del repositorio. Reúne el contenido técnico no redundante de los documentos históricos de arquitectura global, modelo 3D, conductores, regulación convencional Checa y tendido inverso. **No sustituye las ecuaciones del programa ni acredita un diseño ejecutable.**

## 1. Arquitectura de cálculo vigente

La aplicación se presenta desde `main.py`; `motor_general.py` coordina las llamadas, y los módulos no importan los cálculos internos del otro.

- `Analisis_mecanico_conductores/`: catenaria, comportamiento termoelástico, hipótesis, tensiones, flechas, geometría y PDF.
- `Analisis_mecanico_estructuras/`: entradas de postes, esfuerzos preliminares, retenidas, equilibrado, cimentación y salidas; **sin verificación estructural integral aprobada**.
- `calculos/`: modelos de red y ensamblador global en desarrollo.
- `comun/`: catálogo Viakon ACSR único compartido. Las fichas nominales no sustituyen módulos, coeficientes de dilatación o curvas de creep documentados.
- `entradas/`: entradas comunes y conectividad de red.

La interfaz y el motor general deben pasar datos explícitos al módulo que corresponda; las conexiones entre etapas no autorizan emplear aproximaciones geométricas en lugar de resolver el equilibrio.

## 2. Variables y compatibilidad del conductor

Para un vano de cable flexible extensible, se modelan las posiciones y esfuerzos mediante la catenaria hiperbólica exacta cuando la carga vectorial es uniforme por unidad de longitud real, y mediante un problema de contorno espacial cuando el viento depende de la tangente local.

En la formulación BVP, para la coordenada material `s`, posición `r`, vector de tensión `T`, rigidez axial `EA` y cargas `q`:

```text
dr/ds = (1 + |T|/EA) * T/|T|
dT/ds = -(1 + |T|/EA) * (q_gravedad + q_viento(T/|T|))
```

La temperatura introduce deformación térmica `alpha * delta_T` y cambia la compatibilidad de longitud. Deben emplearse los coeficientes y la rigidez correspondientes al estado y conductor documentados; la aproximación lineal no constituye un modelo de creep dependiente del tiempo.

Por cada vano y escenario se conservan:
- Longitud natural de referencia y residuo de compatibilidad, con auditoría independiente cuando exista.
- Tensiones en los dos extremos y máxima tensión total del cable; H horizontal por sí sola no es la demanda máxima.
- Flecha vertical respecto de la cuerda, desviación lateral, coordenadas de la curva y reacciones XYZ.
- Caso físico que gobierna, sin combinar máximos provenientes de escenarios incompatibles.
- Cuando existan alturas y brazos documentados, acciones y momentos de la fuerza en sus puntos de aplicación.

El tendido continuo ideal puede redistribuir material **antes de fijar el conductor**; después del amarre cada vano conserva su longitud natural independiente. Las guías ideales sin fricción pueden resolver otro problema físico, pero **no** representan una grapa real de suspensión.

## 3. Metodología de red tridimensional

Cada red se define como un grafo de apoyos, extremos de amarre y vanos; las conexiones se declaran **en cada extremo y por circuito**. Un apoyo puede tener un circuito en remate y otro en suspensión.

El Excel explícito contempla:

```text
Puntos: Punto | X | Y | Altitud | Poste | Fijacion
Vanos:  Vano | Inicio | Fin | Circuito | Seccion | Conductor |
        Conexion_Inicio | Conexion_Fin | Altura_Inicio_m | Altura_Fin_m
```

Los puntos y las alturas deben estar en sistemas compatibles. Los estados `ANCLAJE`, `FIJA`, `SUSPENSION` y `DESLIZANTE` no son intercambiables. `FIJO` y `MOVIL` describen la condición del apoyo y, para movimiento, requieren rigidez con fuente.

Para apoyos trasladables de rigidez documentada `K`, el residual de equilibrio es:

```text
R_i(u) = suma(F_cables_i(u)) + F_adicionales_i - K_i * u_i
```

El desarrollo global utiliza `scipy.optimize.least_squares` y reevalúa estados del cable con `solve_bvp`. La convergencia numérica se comprueba con residuales físicos; una tolerancia satisfecha no demuestra por sí sola validez constitutiva o experimental.

Las guías `DESLIZANTE` **ideales sin fricción** pueden conservar la longitud natural total y equilibrar las tensiones a ambos lados; la `SUSPENSION` real (grapa, cadena, giro y fricción) exige otra ley mecánica y permanece fuera del alcance validado. No debe reemplazarse por un remate ficticio.

Archivos de referencia: `calculos/modelo_red.py`, `calculos/ensamblador_global.py`, `calculos/hipotesis_red.py`, `entradas/importar_red.py` y regresiones de esos componentes.

## 4. Barridos climáticos y resultados

El análisis de los estados puede generar el producto cartesiano de temperatura, viento y dirección declarados. Se deben conservar todas las filas de cada combinación y no mezclar los casos que producen tensión, flecha o momento máximos.

El barrido histórico de ejemplo usa `incremento_viento_ms=1`, temperaturas explícitas y tensiones iniciales de prueba. **No son parámetros normativos**. El ejemplo `ayuda/ejemplo_barrido_3d.py` tiene EA y alfa **sintéticos**; únicamente verifica el funcionamiento ilustrativo y no debe emplearse para dimensionar una obra.

La geometría entre apoyos no sustituye un perfil de terreno denso, superficie identificada ni obstáculos. Las distancias reales de seguridad se verifican por estado y por vano frente a la topografía y disposición física de fases.

## 5. Tendido inverso: cálculo operativo por vano

Referencias originales: Luis María Checa, *Líneas de Transporte de Energía*, 3.ª ed., capítulo 4, pp. impresas 217–221 y 238–243; resumen ISEP *Cálculo mecánica de conductores aéreos*, pp. 2–6.

Para un único vano con amarres fijos, `dimensionar_tension_tendido` recibe geometría XYZ, peso, diámetro, EA, alfa, temperatura de tendido, fuente material, condiciones climáticas y **límites de tensión con fuente**, además de un intervalo explícito de H. El método evalúa tensiones por hipótesis mediante cable no lineal y selecciona la **mayor H dentro del dominio ensayado** que cumple los límites declarados.

Entrega H de referencia, tensiones en extremos, T máxima, razón T/límite, condición gobernante, flechas, residuales y tabla de tendido a temperaturas declaradas.

La búsqueda verifica monotonía mediante muestras; **no demuestra monotonía global**. Si una cota numérica de exploración gobierna, debe informarse como **límite de búsqueda**, no como tensión normativa óptima.

Las fórmulas simplificadas citadas por ISEP:

```text
f ≈ g * a²/(8*P)
L ≈ a + g²*a³/(24*P²)
```

son aproximaciones parabólicas de referencia, no sustitutos del motor de catenaria exacta o BVP.

## 6. Regulación convencional multivano (Checa): referencia histórica, no modelo principal

Referencia: Checa, 3.ª ed., capítulo 4 §4.2, pp. impresas 245–247, ecuaciones (42)–(44). Para luces aproximadamente horizontales:

```text
a_reg = sqrt( suma(a_i³) / suma(a_i) )
```

Es un **indicador de regulación parabólico convencional**. No calcula tensiones de tendido ni capacidades resistentes, ni debe introducirse como entrada de la catenaria exacta para sustituir cada vano.

La formulación convencional histórica analizaba una sección entre amarres con H común, suma de longitudes naturales y viento transversal local de envolvente. La carga de referencia era `w_v = 0.5*rho*Cd*d*V²/1000` en kN/m. Este supuesto es distinto de aplicar una **dirección geográfica única de viento** a una red 3D.

Las hojas `Puntos`, `Materiales`, `Hipotesis` y, cuando proceda, `Vanos`, documentan la procedencia de geometría y límites. Si hay remates intermedios o secciones distintas no deben unirse artificialmente. Tras el amarre fijo, **los vanos no redistribuyen sus longitudes naturales**.

Los ensayos de este enfoque histórico permanecen como referencias de comparación en `tests/test_regulacion_multivano.py` y `tests/test_integracion_regulacion_fase1.py`. No debe confundirse su alcance convencional con la formulación operativa actual por vano fijo.

## 7. Fuentes y criterios físicos

- **Viakon (junio 2020)**, *Manual del Electricista*, pp. impresas 18–20: masa, diámetro, construcción y carga de ruptura nominal de ACSR por calibre y nombre del ave. La ruptura **no** es tensión admisible. Fuente: https://viakon.com/wp-content/uploads/2020/11/ManualElectricista_2020.pdf
- **Nexans**, *T-ACSR Cable Stress and Strain Characteristics*: referencias de E y alfa inicial/final por construcción; **no acreditan automáticamente** propiedades de un conductor Viakon. Fuente: https://www.nexans.com.br/.rest/eservice/dam/v1/file/223724/StressStrainACSR_es.pdf
- **Trefinasa**, *Overhead Conductors, ACSR*: contraste secundario de propiedades mecánicas según construcción. Fuente: https://www.trefinasa.com/wp-content/uploads/2017/04/overhead_conductors_trefinasa_2016web.pdf
- **CFE 2014**, manual de instalaciones aéreas MT/BT: criterios de hipótesis, tensiones y distancias; el detalle y las advertencias de extracción se conservan en `ayuda/criterios_documentados_cfe_2014.md`.
- **Checa e ISEP**: referencias de derivaciones tradicionales; sus simplificaciones no sustituyen la física del modelo vigente ni son normas hondureñas.

Se distingue obligatoriamente entre tensión máxima total, H horizontal, porcentaje de ruptura, porcentaje de utilización normativa y residual numérico. Ninguno de ellos, por sí solo, acredita cumplimiento estructural.

## 8. Validación y límites reconocidos

Las pruebas incluyen contraste con catenaria analítica, estados térmicos, viento oblicuo, residuales, compatibilidad, coordenadas UTM grandes, rotación y reversión del vano, envolventes e invariancia de unidades, además de las regresiones CFE.

Una referencia CFE RAVEN a 50 °C verifica H y flecha tabuladas con P publicado, pero **no** valida la obtención de P, el creep ni toda la física multivano.

Siguen fuera del alcance certificado:
- Fluencia/creep predictivo y curvas completas tensión-deformación ACSR por fabricante.
- Suspensiones reales, fricción, dinámica, vibración, fatiga y viento turbulento cuando proceda.
- Postes con seis grados de libertad, rigidez no documentada y desplazamientos acoplados.
- Retenidas con holgura/pretensado, anclajes y comportamiento unilateral; interacción suelo-cimentación.
- Capacidad documentada de poste, cruceta, aislador, grapa y herrajes, más combinaciones de cargas.
- Despejes contra terreno real y obstáculos con topografía y disposición de fases verificadas.

Los resultados estructurales preliminares permanecen **NO VERIFICABLE** mientras falten capacidades materiales o geometría. Las regresiones comprueban el software dentro de su alcance, **no certifican diseños de obra**.

## 9. Ejecución y trazabilidad

```bash
streamlit run app.py
python -m unittest discover -s tests -p 'test_*.py' -v
python -m unittest discover -s Analisis_mecanico_conductores/pruebas -p 'test_*.py' -v
python tools/auditar_codigo.py
python -m ayuda.ejemplo_barrido_3d
```

Las modificaciones del motor, los límites y la procedencia documental se conservan en el historial de commits y las regresiones; **no** se mantienen versiones sucesivas del mismo manual dentro de esta carpeta.
