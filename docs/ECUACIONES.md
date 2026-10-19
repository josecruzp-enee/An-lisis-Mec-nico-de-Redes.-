# Inventario matemático

Estas son **deducciones de mecánica clásica e hipótesis explícitas**, no citas
verificadas del Manual ENEE. No se atribuyen páginas ni numerales no consultados.

Unidades: m, kN, kN/m de cable real, kN·m, rad y °C. Global: X Este, Y Norte,
Z arriba. Azimut matemático: 0° Este, 90° Norte, viento HACIA esa dirección.

## Catenaria espacial: catenaria.py

Carga constante q por longitud real. w=|q|; n=-q/w. Para extremos A,B:
Δz=(B-A)·n, D=B-A-Δz n, L=|D|, e=D/L, a=H/w.

`xc = L/2 - a asinh(Δz / (2 a sinh(L/(2a))))`

`r(x) = A + x e + 2 a sinh(x/(2a)) sinh((x/2-xc)/a) n`

`T(x) = H cosh((x-xc)/a)`

`S = 2 a sinh(L/(2a)) cosh((L/2-xc)/a)`

Fuerzas del cable SOBRE los apoyos:
`FA = H[e + sinh(-xc/a)n]`, `FB = -H[e + sinh((L-xc)/a)n]`.
Control independiente: `FA + FB = q S`.

H es perpendicular a q. Con viento no es necesariamente la componente
horizontal global. Debe compararse RTS con tensión total máxima de extremos.
La formulación exige w>0 y L>0. Cable recto descargado es un límite, no se
simula con una catenaria indeterminada. Sin viento sigue existiendo peso.

Mínimo de `r(x)·v - m x`: evaluar extremos y
`x=xc+a asinh((m-e·v)/(n·v))`, si n·v>0 y x pertenece al vano.
Así el despeje mínimo no depende de la cantidad de puntos del gráfico.
Terreno lineal entre bases; **no representa obstáculos, terreno transversal ni
libramientos eléctricos fase-fase**. El perfil Excel exige altura sobre terreno
(o longitud total menos empotramiento y offset); no mezcla ambas longitudes.

## Compatibilidad: cambio_estado.py

Elasticidad lineal con rigidez axial EA específica del cable:
`S0 = integral[ds/(1+T(s)/EA)]`.

Estado final:
`S0_final(H) = S0_inicial * (1 + alpha ΔT + epsilon_permanente)`.

Integración Gauss-Legendre de 64 puntos; comprobación con 128 en pruebas.
Bisección con intervalo positivo y residual absoluto de longitud ≤1e-8 m.
Tolerancia e iteraciones se guardan. Sin raíz/convergencia se levanta error.
Creep es una deformación permanente dada; no se predice envejecimiento.
Se asume carga q uniforme sobre longitud deformada: aproximación de carga
compatible con pequeñas deformaciones axiales, documentada como limitación.

El solver permite sumas de vanos con H común como sección deslizante ideal.
El orquestador sólo acepta vanos retenidos. No representa cadenas de suspensión
finitas ni demuestra compatibilidad de una línea real con apoyos móviles.
Vano regulador auxiliar: `sqrt(sum(L³)/sum(L))`, no usado para aprobar.

## Cargas: cargas_espaciales.py y viento.py

Velocidad transversal `Vn = V·normal_horizontal_vano`.
`qv = 0.5 rho Cd (D+2t) Vn |Vn| /1000` en kN/m.
Hielo: `qh = rho_hielo π[(D+2t)²-D²] g/(4*1000)`.
Carga global: `q = qv normal + (0,0,-peso-qh)`.
Cd, densidad y hielo son parámetros de cálculo, no factores normativos.
Se desprecia variación del arrastre con la tangente de la catenaria.

Equipos, viento de poste y accesorios, construcción y mantenimiento se ingresan
como acciones adicionales documentadas. No se calculan automáticamente sin
áreas proyectadas, centroides y criterios. Una fuerza se aplica en su r real.
`Ftotal=ΣFi`; `Mtotal=Σ(ri×Fi)+ΣMi`.

Combinaciones aplican factores explícitos a acciones resueltas. No convierten
un estado de servicio en otro estado térmico ni incorporan normas implícitas.
Envolventes guardan máximo absoluto y caso; no forman un vector simultáneo
ficticio juntando máximos de casos diferentes.

## Poste y retenidas: retenidas_espaciales.py

Modelo reducido de 6 grados de libertad con K simétrica definida positiva.
`u_amarre=B u`, `B=[I,-[r]x]`. Rotaciones pequeñas; no es un análisis de elementos
finitos de un poste real. K y su fuente deben suministrarse explícitamente.

Cable con EA, pretensión T0 y longitud inicial L:
`L0=L/(1+T0/EA)`, `T=max(EA*(l/L0-1),0)`.
Cables flojos no resisten compresión. Geometría y tangente se actualizan durante
Newton amortiguado; nunca se reparte H/n ni se impone 45°.

Equilibrio generalizado `K u + ΣBᵀ T n = Fexterna`.
Resultado: desplazamientos, acciones residuales del poste, fuerzas de cada
retenida, compresión añadida, iteraciones y residual ≤1e-8 en componentes mixtas
(kN y kN·m). Escalar correctamente el sistema en futuras extensiones muy rígidas.
K singular, paso no descendente o no convergencia bloquean resultado.

Para cálculo manual del anclaje a 3 m y amarre 10 m, si una sola retenida
alineada equilibra H: `T=H sqrt(3²+10²)/3`, `V=H*10/3`.
El motor general no impone que la retenida equilibre toda H: comparte con K.

## Resistencia, anclaje y suelo

Comparación básica `utilización=demanda/capacidad` sólo con fuente, tipo
admisible/diseño y método compatible. RTS no es resistencia admisible.
Flexión biaxial no se reduce a una carga nominal de ensayo.
Interacción lineal `N/Nd + |Mx|/Mxd + |My|/Myd` sólo si se solicita ese criterio
con fuente; no es una ley universal para concreto/madera/acero/PRFV.

Cable, fijación, herrajes, varilla, ancla y suelo se comprueban separadamente
contra T en su dirección real. Capacidades introducidas deben ser para ese
arreglo y esa dirección; el motor no deduce la capacidad geotécnica.
Cimentación: comparaciones parciales de lateral, momento, compresión, extracción.
Estabilidad, interacción, desplazamiento, rotación y resistencia estructural
sin modelo específico permanecen NO VERIFICABLE, incluso si las comparaciones
parciales pasan. `R=M/d` heredado es sólo indicador, jamás aprobación.
