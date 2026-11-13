# Motor matemático 3D — fase de integración

Los módulos nuevos viven en `calculos/` y **no sustituyen** todavía el
motor llamado por `main.py`, que permanece con resultados preliminares.

| Módulo | Función |
|---|---|
| `validacion_mecanica.py` | Dominio numérico finito, vectores 3D |
| `catenaria.py` | Solución cerrada de cable flexible con carga vectorial uniforme por longitud real |
| `cambio_estado.py` | Compatibilidad termoelástica de longitud, cuadratura e iteración con residual |
| `cargas_espaciales.py` | Cargas 3D y resultantes 6D |
| `barrido_3d.py` | Barrido de viento, dirección, temperatura y tensión inicial; acciones en nodos |

## Arquitectura matemática

1. Referencia: conductor a `temperatura_tendido_C`, sin viento, con H inicial explícita.
2. Condición final: carga por peso y viento, temperatura, EA, alfa y geometría XYZ.
3. Resuelve compatibilidad de longitud natural para hallar nueva H.
4. Reconstruye catenaria 3D, tensiones en los extremos y reacciones.
5. Acumula fuerzas y momentos con el brazo real de los amarres.
6. Conserva resultados completos por cada estado; no mezcla máximos de estados distintos.

**Velocidad:** intervalo configurable con `incremento_viento_ms=1`, incluyendo extremos.
**Tensiones:** lista explícita `tensiones_iniciales_kN=[4,6,8,...]`.
**Temperaturas/direcciones:** listas explícitas que forman el producto cartesiano.

Secciones modeladas: **vanos individualmente retenidos** con extremos fijos.
No hay deslizamiento de conductor por suspensión ni interacción de apoyos flexibles.

## Dominio de validez pendiente de ampliar

La catenaria es exacta **solamente respecto de una carga vectorial constante por
unidad de longitud real**. El viento, por ahora, es calculado normal al eje
horizontal del vano, no a la tangente local en cada punto. Para un modelo de
arrastre variable sobre la curva hará falta un problema de contorno no lineal
con carga aerodinámica local y compatibilidad acoplada, seguido de validaciones
independientes. El modelo actual **no debe presentarse como solución completa
de viento real**. Tampoco considera ráfagas transitorias, vibraciones, hielo,
fluencia modelada, tensión individual fase por fase ni desplazamiento del apoyo.

La base de terreno entre apoyos tampoco permite verificar libramientos reales
sin perfil de terreno y obstáculos. Capacidad de poste, anclajes y cimentación
siguen **NO VERIFICABLE** y requieren datos de ensayo/geotecnia.

## Ejecutar

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m ayuda.ejemplo_barrido_3d
```

El ejemplo emplea EA y alfa **sintéticos**, expresamente no válidos para
dimensionar una línea real. No sustituir esos valores por supuestos genéricos.
No publicar decisiones CUMPLE antes de completar la verificación técnica.
