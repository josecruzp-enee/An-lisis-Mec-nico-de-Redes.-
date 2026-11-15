# Módulo 01 — Regulación convencional multivano (Checa)

## Referencia principal

Luis María Checa, *Líneas de Transporte de Energía*, 3.ª edición,
capítulo 4, §4.2, páginas impresas **245–247**.
Las ecuaciones (42)–(44) desarrollan el vano ideal de regulación
para una sección de tendido con varios vanos.

Para luces `a_i` aproximadamente horizontales:

```text
a_reg = sqrt( sum(a_i^3) / sum(a_i) )
```

La expresión es un equivalente de la APROXIMACIÓN parabólica.
No determina por sí sola la tensión inicial ni la admisibilidad.

## Método implementado

`calculos/regulacion_multivano.py`:

1. Lee los postes ordenados y calcula cada luz horizontal real.
2. Identifica una sección convencional de regulación, entre sus extremos.
3. Recupera, mediante catenaria por vano, la longitud natural de
   referencia para una tensión H inicial candidata.
4. Para cada hipótesis, obtiene la nueva H común de la sección mediante
   **conservación de la suma de longitudes naturales** considerando
   temperatura y cambio de carga. Utiliza el solucionador de
   `calculos/cambio_estado.py`, comprobado previamente contra el BVP.
5. Calcula la tensión máxima de cada vano en ambos extremos y comprueba
   sus límites documentados.
6. Determina el mayor H de referencia compatible con TODAS las
   hipótesis, dentro del dominio numérico declarado.
7. Calcula flechas por vano e hipótesis y la tabla de tendido a
   0, 10, 20, 30 y 40 °C.

No sustituye la geometría de todos los vanos por una sola catenaria
del vano regulador. Este se informa como indicador de la sección.

La carga transversal de viento corresponde a la **envolvente local**
(velocidad de viento normal a cada vano), no a una sola dirección
geográfica del viento que afecte simultáneamente a todos los tramos.
La fórmula aerodinámica usada es
`w_v = 0.5*rho*Cd*d*V^2/1000` en kN/m.
La componente longitudinal de viento se omite conforme a esa hipótesis
de carga transversal convencional.

## Interfaz y entradas

En Fase 1, modo normal **Calcular automáticamente**:

- Un Excel contiene `Puntos`, `Materiales` e `Hipotesis`.
- `Puntos`: Punto, X, Y y opcionalmente Altitud/Altura_Amarre_m.
  Si estas columnas no existen, la sección se toma nivelada a
  una cota de referencia arbitraria de cero.
- `Materiales`: Conductor, EA_kN, Alpha_por_C,
  Temperatura_tendido_C y Fuente. Peso y diámetro proceden de Viakon.
- `Hipotesis`: Hipotesis, Temperatura_C, Viento_ms,
  T_limite_kN, Fuente_limite, Criterio_diseno.
- La hoja `Vanos` es opcional; si declara remates intermedios o
  secciones diferentes, el sistema se niega a calcularlas como una sola.

La H inicial de la sección **se obtiene por cálculo**, no se solicita
ni figura entre las columnas de la plantilla.

## Resultados

- Vano regulador (m) y longitud de sección.
- H calculada al tendido, hipótesis gobernante y relación máxima
  de tensión a límite.
- H de cada hipótesis, tensión máxima de sección y residual.
- Flecha individual de cada vano por hipótesis.
- Tabla de tensión y flecha de cada vano por temperatura.
- Exportación CSV en la pantalla principal.

## Límites — indispensables

El programa no determina tensiones admisibles sin criterios de diseño
aportados con fuente. La carga de ruptura Viakon NO es la tensión
admisible de servicio.

La hipótesis de tensión común constituye un **modelo convencional
de regulación**: presupone redistribución compatible de cable en una
sección, no describe rozamiento real de grapas ni postes deformables.
No sirve para calcular fuerzas EXACTAS en el herraje intermedio.

La versión convencional requiere amarres de la misma cota. Para
grandes desniveles, herrajes que bloqueen deslizamiento y análisis
3D con viento geográfico, se utiliza el motor 3D y condiciones de
conexión apropiadas.

El intervalo automático de H usa porcentajes de ruptura SOLO como
dominio numérico provisional. Si queda activa la cota superior, debe
informarse **LÍMITE DE BÚSQUEDA**, no «óptimo físico».

No se comprueban perfiles topográficos, libramientos, comportamiento
de creep ni resistencia de postes, retenidas o cimentación.

## Pruebas y estado

- `tests/test_regulacion_multivano.py`:
  vano equivalente, tensión/flechas, cambio térmico, comparación
  independiente de un vano con BVP, rechazo de desniveles y fuentes.
- `tests/test_integracion_regulacion_fase1.py`:
  Excel con tres postes, plantillas sin H ficticia, hipótesis
  climáticas y rechazo de retenciones intermedias.

**Alcance de esta etapa:** flujo convencional de cálculo mecánico
de conductores en sección reguladora aproximadamente horizontal,
NO verificación estructural completa.
