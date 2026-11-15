# ETAPA 1 — Análisis mecánico de conductores

## Propósito

Este paquete contiene **una única implementación canónica** para el
cálculo mecánico de conductores aéreos. Corresponde a la **Etapa 1** del
proyecto. No incluye dimensionamiento de postes, retenidas ni cimentaciones.

**Nombre del paquete:** `Analisis_mecanico_conductores`

## Organización de los archivos

| Carpeta | Archivo | Responsabilidad |
| --- | --- | --- |
| `validaciones/` | `validar_datos_fisicos.py` | Asegurar unidades, números finitos y puntos válidos |
| `geometria/` | `calcular_vanos_y_vano_regulador.py` | Obtener luces, azimuts y vano ideal según Checa |
| `conductores/` | `catalogo_acsr_viakon.py` | Ficha nominal ACSR con fuente del fabricante |
| `conductores/` | `referencias_mecanicas_acsr_nexans.py` | EA y dilatación **comparativos**, no certificados Viakon |
| `catenaria/` | `resolver_catenaria_exacta.py` | Catenaria bajo carga constante, longitudes y tracciones |
| `catenaria/` | `resolver_cable_tridimensional_bvp.py` | Cable 3D con viento sobre tangente local |
| `cambio_estado/` | `resolver_cambio_de_estado.py` | Compatibilidad de longitudes y cambio térmico |
| `hipotesis_climaticas/` | `evaluar_estados_climaticos_catenaria_3d.py` | Barrido analítico de cargas y temperaturas |
| `hipotesis_climaticas/` | `evaluar_estados_climaticos_bvp_3d.py` | Barrido físico BVP por vano |
| `tension_tendido/` | `calcular_tension_y_flechas_de_seccion.py` | Regulación convencional multivano |
| `tension_tendido/` | `evaluar_estados_de_la_seccion.py` | Evaluar cargas y tensiones por estado climático mediante un motor único |
| `tension_tendido/` | `construir_resultados_regulacion.py` | Crear tablas de hipótesis, flechas y tendido sin recalcular la física |
| `tension_tendido/` | `calcular_tension_inversa_de_un_vano.py` | Optimización inversa 3D de un vano fijo |
| `tension_tendido/` | `resolver_seccion_deslizante_ideal.py` | Sección con guías ideales sin fricción, distinta de una grapa real |
| `flechas/` | `calcular_flecha_vertical_de_catenaria.py` | Flecha vertical de catenaria con amarres nivelados |
| `verificaciones/` | `resumir_calidad_numerica_bvp.py` | Indicadores de convergencia y calidad del BVP |
| `conductores/` | `mostrar_tabla_catalogo_acsr.py` | Tabla consultable de conductores |
| `interfaz/` | `mostrar_tendido_inverso_un_vano.py` | Interfaz heredada de análisis inverso univano |
| `entradas/` | `leer_tension_inversa_desde_excel_historico.py` | Compatibilidad de formato Excel univano anterior |
| `verificaciones/` | `comparar_tension_con_rotura_acsr.py` | Diagnóstico respecto de ruptura nominal |
| `verificaciones/` | `verificar_limites_documentados_de_tension.py` | Comparación contra hipótesis admisibles |
| `entradas/` | `leer_datos_y_calcular_regulacion.py` | Adaptar Excel a cálculo convencional |
| `interfaz/` | `mostrar_analisis_de_conductores.py` | Capturar parámetros en Streamlit sin modificar Excel |
| `pruebas/` | `test_identidad_de_importaciones.py` | Verifica que ambas rutas importan la misma función |

## Refactorización de regulación (sin cambios de modelo)

La función pública `resolver_seccion_regulacion` sigue siendo el
punto de entrada de la Etapa 1. Conserva su firma, sus resultados,
sus validaciones y la selección de tensión bajo hipótesis documentadas.

Ahora delega en:
- `EvaluadorEstadosRegulacion.evaluar_estado()`: estados por
  temperatura y viento, compatibilidad de longitudes y tensiones
  de extremo
- `construir_tablas_de_hipotesis()`: tabla de estados y flechas
- `construir_tabla_de_tendido()`: tabla a temperaturas sin viento
- `calcular_flecha_vertical_de_catenaria()`: mínima elevación del
  conductor respecto de amarres nivelados

La clase evaluadora mantiene caché de estados repetidos, y no
crea ninguna segunda formulación física.

**Regresión:** añadir y conservar pruebas de la interfaz pública y de
los resultados numéricos. Todas las propiedades y límites de ensayos
de código son sintéticos y no equivalen a diseño autorizado.

## Propiedades ENEE disponibles automáticamente

- Datos: `conductores/propiedades_mecanicas_acsr_enee.json` (11 ACSR,
  Tabla 16, valores originales sin modificación).
- Lector único: `conductores/seleccionar_propiedades_enee.py`.
- Se identifica cada construcción por **calibre y ave** (p. ej.
  `2/0` + `QUAIL`), sin seleccionar únicamente por calibre.
- **E inicial/final** se elige explícitamente. La conversión es
  `EA_kN = E_kgf_mm2 × A_mm2 × 9.80665 / 1000`.
- Peso, diámetro, ruptura y dilatación se toman de **la misma ficha
  ENEE**, sin combinarlos con datos Viakon.
- **Streamlit:** opción `ENEE — Tabla 16` en propiedades termoelásticas,
  más selector de estado `Inicial` o `Final`.
- **Excel:** hoja `Materiales`, columnas `Fuente_Propiedades=ENEE`
  y `Estado_Elasticidad=Final` (o `Inicial`). Se exige temperatura de
  tendido, hipótesis climáticas y límites documentados.
- El modo manual y la referencia Nexans se conservan para compatibilidad.
  El catálogo Viakon sigue independiente.

**Límite técnico:** seleccionar E final no representa por sí mismo
fluencia ni permite afirmar que se ha calculado una flecha final
dependiente del tiempo. K y K' están archivados, pero aún no integrados
en las ecuaciones.

## Dependencias y compatibilidad

Las rutas anteriores en `calculos/` y `entradas/` **no contienen ya
los motores listados arriba**: son archivos pequeños que importan
los mismos objetos desde este paquete. Conservan los importadores
existentes mientras se adapta el software.

No eliminar ni introducir nuevas ecuaciones en esos adaptadores.
Para realizar un cambio técnico, editar únicamente la implementación
canónica situada en esta carpeta, y añadir pruebas.

El motor de postes, retenidas, cimentación, perfiles y evaluaciones
estructurales sigue **fuera de este paquete** y no se reorganiza aún.

Las interfaces históricas de barrido 3D y tendido inverso siguen
disponibles para compatibilidad; su unificación visual no se considera
completada por el mero traslado del motor.

## Contratos de mantenimiento

- **Un archivo, una responsabilidad técnica.** Un nombre debe indicar
  qué cálculo realiza; evitar nombres vagos como `utils.py`.
- **Funciones breves y específicas.** Separar lectura, validación,
  física, selección de estado gobernante y construcción de resultados.
- **Docstrings técnicos obligatorios** para nuevas funciones públicas:
  unidades, argumentos, valores devueltos, hipótesis y errores.
- **Sin supuestos silenciosos.** No inventar EA, dilatación,
  límites admisibles, alturas de amarre ni viento de diseño.
- **No confundir modelos.** Vano regulador Checa es una aproximación
  convencional; BVP 3D sirve para geometría y carga más generales.
- **Sin modificar módulos de otras etapas** salvo adaptaciones de
  importación compatibles, acompañadas de regresiones.

## Alcance que falta cerrar, antes de Etapa 2

1. Selección documentada de propiedades completas del conductor.
2. Hipótesis climáticas y tensiones admisibles con fuentes del proyecto.
3. Tratamiento integrado de vanos desnivelados y secciones diferenciadas.
4. Validación numérica completa frente a casos de Checa y proyectos reales.
5. Una sola interfaz y memoria técnica de tensiones/flechas.
6. Refactor gradual de funciones heredadas que siguen siendo largas
   (sin cambiar ecuaciones ni resultados mientras se reorganiza).

**Regla de proyecto:** no comenzar la siguiente etapa hasta que el
cálculo de conductores esté validado y operativamente cerrado.

## Referencias

- Luis María Checa, *Líneas de Transporte de Energía*, 3.ª ed.,
  capítulo 4: cálculo mecánico de conductores y vano ideal de regulación.
- Viakon, *Manual del Electricista* (2020), tablas ACSR.
- Nexans, *Stress and Strain Characteristics of ACSR* (referencia
  de propiedades finales por construcción, no certificación Viakon).
