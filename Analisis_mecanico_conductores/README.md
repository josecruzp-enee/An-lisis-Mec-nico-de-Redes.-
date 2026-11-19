# Módulo 1 — Análisis mecánico de conductores

**Repositorio:** Análisis Mecánico de Redes de Distribución  
**Paquete:** `Analisis_mecanico_conductores/`  
**Última revisión documental:** 19 de noviembre de 2026  
**Alcance:** geometría, catenaria, compatibilidad termoelástica, condiciones de tendido, hipótesis climáticas, verificaciones de conductor, red mecánica parcial y memorias PDF. **No dimensiona ni aprueba postes, crucetas, grapas, cimentaciones o retenidas.**

Este documento describe **lo que realmente implementa el código**. Se distinguen las rutas de cálculo en lugar de presentar como equivalentes formulaciones diferentes. No es una nueva certificación física del motor ni altera sus ecuaciones.

## 1. Organización y responsabilidades

| Ruta | Responsabilidad | Implementaciones representativas |
|---|---|---|
| `conductores/` | Identificación y propiedades trazables ACSR | `seleccionar_propiedades_enee.py`, `referencias_mecanicas_acsr_nexans.py`, JSON ENEE |
| `entradas/` | Validación/importación Excel e hipótesis | `importar_red.py`, `importar_hipotesis_red.py`, `hipotesis_tendido.py`, adaptadores Excel |
| `validaciones/` | Reexportación de validación física compartida desde `comun/` | `validar_datos_fisicos.py` |
| `geometria/` | Luces, azimuts y descripción de vanos | `resumir_vanos.py` |
| `catenaria/` | Geometría exacta bajo carga uniforme y BVP 3D | `resolver_catenaria_exacta.py`, `resolver_cable_tridimensional_bvp.py` |
| `cambio_estado/` | Integración de longitud natural y compatibilidad térmica | `resolver_cambio_de_estado.py` |
| `tension_tendido/` | Determinación de H, hipótesis CFE, amarres fijos y sección deslizante | `calcular_tension_y_flechas_de_seccion.py`, `ejecutar_corridas_cfe_documentadas.py`, `resolver_seccion_deslizante_ideal.py` |
| `flechas/` | Flecha respecto de cuerda y desplazamiento lateral | `calcular_desplazamientos_catenaria_3d.py` |
| `hipotesis_climaticas/` | Barridos de temperatura, viento, hielo y BVP | `generar_barrido_de_temperatura_viento_hielo.py`, `evaluar_estados_climaticos_bvp_3d.py` |
| `verificaciones/` | Límites documentados, calidad numérica, requisitos CFE | `verificar_restricciones_documentadas_cfe.py`, `evaluar_requisitos_cfe_por_vano.py` |
| `calculos/` | Topología y ensamblador parcial de red | `modelo_red.py`, `ensamblador_global.py`, `hipotesis_red.py`, `barrido_global.py` |
| `topografia/` | Elevaciones y libramientos **muestreados**, preliminares | `modelo_terreno.py` |
| `interfaz/` | Presentación y captura Streamlit; no debe definir física | `mostrar_analisis_de_conductores.py`, `mostrar_corridas_cfe_documentadas.py`, `mostrar_red_global.py` |
| `salidas/PDF/` | Formateo, gráficos y combinación de memorias; no recalcula ingeniería | `generar_pdf_etapa_1.py`, `generar_pdf_corrida_cfe.py`, `coordinar_pdf.py` |
| `pruebas/` | Ensayos de regresión internos del módulo | `test_*.py` |

`README.md` documenta el módulo; los `__init__.py` identifican paquetes Python. Los catálogos CFE de limitaciones estructurales son **referencias documentales**, no sustituyen el cálculo del Módulo 2.

## 2. Convenciones físicas y unidades

- Coordenadas: **X Este, Y Norte, Z arriba**, en metros. Altura del amarre: `Z = Altitud + Altura_Amarre_m` cuando ambas columnas están presentes.
- `L`: luz horizontal o proyección perpendicular a la carga, según la ecuación indicada; **no intercambiarlas**.
- `w`: peso por longitud real, kN/m. `q`: carga vectorial por longitud real de conductor, kN/m.
- `H`: parámetro de tensión perpendicular a la carga resultante en la catenaria exacta. **Con viento, no es necesariamente la componente horizontal geográfica ni la tensión total**.
- `T`: módulo de tracción del conductor, kN. `EA`: rigidez axial, kN. `alpha`: 1/°C.
- `RTS`: carga nominal de rotura; la comparación porcentual aplica a `T_max` salvo donde una regla publicada limite explícitamente otra magnitud.
- `Cd`, `rho`, diámetro y viento son datos explícitos. El modelo BVP admite velocidad en m/s; las tablas CFE reciben km/h y convierten mediante `/3.6`.

**Regla fundamental:** el modelo no transforma por defecto un ensayo sintético en ficha certificada ni equipara datos de ENEE, CFE, Viakon y Nexans sin trazabilidad.

## 3. Recorrido matemático: cálculo general de un conductor con vanos amarrados

| Paso matemático | Ecuación o condición efectivamente implementada | Archivo / función |
|---|---|---|
| **1. Leer geometría** | `A_i=(X_i,Y_i,Z_i)`, `L_i=sqrt((ΔX)^2+(ΔY)^2)`; rechazar vanos de luz cero y entradas parciales inconsistentes | `entradas/leer_datos_y_calcular_regulacion.py::ejecutar_regulacion_fase1`; `tension_tendido/calcular_tension_y_flechas_de_seccion.py::_geometria`; `geometria/resumir_vanos.py::resumen_geometrico` |
| **2. Identificar conductor** | `EA = E·A` con conversión de unidades; seleccionar propiedades de una misma fuente para el estado inicial/final elegido | `conductores/seleccionar_propiedades_enee.py::seleccionar_conductor_enee`; `::seleccionar_desde_clave_viakon` |
| **3. Preparar carga gravitatoria** | `q_g=(0,0,-w)` | `tension_tendido/evaluar_estados_de_la_seccion.py::calcular_cargas_transversales_por_vano` |
| **4. Aplicar viento según el modo de cálculo** | **General:** `w_v = rho·Cd·D·V²/2000` [kN/m], sin dependencia explícita del claro. **CFE tabulado:** `w_v,i = p_CFE(L_i, V)·D/1000` [kN/m], con presión en Pa específica de la luz horizontal `L_i` de cada vano. En ambas rutas la carga convencional es perpendicular al vano en planta. | `tension_tendido/evaluar_estados_de_la_seccion.py::calcular_cargas_transversales_por_vano`; para CFE, `hipotesis_climaticas/presiones_cfe_por_claro.py::presion_cfe_por_claro` |
| **5. Resolver catenaria exacta** | `a=H/|q|`; `z(x)=a[cosh((x-xc)/a)-cosh(xc/a)]`; `T(x)=H cosh((x-xc)/a)` | `catenaria/resolver_catenaria_exacta.py::resolver_catenaria`; métodos `Catenaria.puntos`, `.tension` |
| **6. Fijar extremos desnivelados** | `xc=L/2 - a·asinh(Δz/[2a sinh(L/(2a))])`; la coordenada `z` es local y está orientada opuesta a `q` | `catenaria/resolver_catenaria_exacta.py::resolver_catenaria` |
| **7. Obtener longitud de arco** | `S=2a sinh(L/(2a)) cosh((L/2-xc)/a)` | `catenaria/resolver_catenaria_exacta.py::Catenaria.longitud` |
| **8. Obtener longitud natural** | `S_n = integral_0^L [cosh((x-xc)/a)/(1+T(x)/EA)] dx`; cuadratura Gauss-Legendre, adaptación si hace falta, **sin parábola** | `cambio_estado/resolver_cambio_de_estado.py::longitud_natural` |
| **9. Cambiar estado térmico** | `S_{n,obj}=S_{n,ref}·[1+alpha·(theta-theta_ref)+epsilon_perm]` | `cambio_estado/resolver_cambio_de_estado.py::resolver_cambio_estado` |
| **10. Resolver la nueva H** | Encontrar raíz de `F(H)=S_n(H,q_estado,EA)-S_{n,obj}=0`, usando `brentq` y control de residuo | `cambio_estado/resolver_cambio_de_estado.py::resolver_cambio_estado`; `tension_tendido/evaluar_vanos_amarrados_independientes.py::EvaluadorVanosAmarrados._resolver_por_longitud` |
| **11. Conservar amarres por vano** | Una vez fijado el cable, **cada** vano `i` mantiene su propia `S_{n,i}`. Puede resultar `H_i(theta,V) != H_j(theta,V)`; no redistribuye longitud entre espigas | `tension_tendido/evaluar_vanos_amarrados_independientes.py::EvaluadorVanosAmarrados.evaluar_estado` y `evaluar_estado_con_hielo` |
| **12. Calcular máximo de tracción** | `T_max,i = max[T_i(0),T_i(L_i)]` en la catenaria uniforme; no confundirlo con `H_i` | Evaluador anterior; `catenaria/resolver_catenaria_exacta.py::Catenaria.tension` |
| **13. Verificar todas las hipótesis** | `U(H_ref) = max_{caso,i} (T_max,caso,i/T_limite,caso)`; condición `U<=1` | `tension_tendido/calcular_tension_y_flechas_de_seccion.py::resolver_seccion_regulacion` |
| **14. Dimensionar H de tendido** | Buscar el mayor valor admisible de `H_ref` dentro del intervalo indicado, verificando monotonicidad en este procedimiento específico y resolviendo `U(H_ref)-1=0` | `tension_tendido/calcular_tension_y_flechas_de_seccion.py::resolver_seccion_regulacion` |
| **15. Flecha y desviación** | Comparar puntos de la catenaria con la **cuerda entre amarres**; máximo descenso vertical y máximo desplazamiento lateral respecto de ella | `flechas/calcular_desplazamientos_catenaria_3d.py::calcular_flecha_y_desviacion_3d` |
| **16. Tablas** | Registrar por hipótesis `H_i`, `T_max,i`, `f_i`, límites, utilización y residuales; generar tabla de tendido a temperaturas solicitadas | `tension_tendido/construir_resultados_regulacion.py::construir_tablas_de_hipotesis`, `::construir_tabla_de_tendido` |
| **17. Barrido opcional** | Repetir para temperaturas, viento e hielo solicitados **a partir de la H determinada**, sin sustituir el criterio normativo | `hipotesis_climaticas/generar_barrido_de_temperatura_viento_hielo.py::ejecutar_barrido_climatico` |
| **18. Salida** | Convertir resultados ya calculados en tablas, gráficos y PDF | `salidas/PDF/generar_pdf_etapa_1.py::generar_pdf_etapa_1`; `salidas/PDF/coordinar_pdf.py::generar_memoria_pdf` |

### 3.1 Importante: condición de tendido frente a condición después del amarre

La **misma** `H_ref` propuesta sirve como condición de instalación para dimensionar todos los vanos. Después de fijarlos, **cada vano conserva su propia longitud natural** y el cambio de temperatura o viento produce tensiones individuales. El campo `vano_regulador_m` permanece únicamente por compatibilidad de salida histórica: **no condiciona las ecuaciones de este flujo**.

La función `EvaluadorEstadosRegulacion.evaluar_estado` en `tension_tendido/evaluar_estados_de_la_seccion.py` conserva una **H común** por sección bajo guía ideal: constituye una formulación distinta, **no** la utilizada para el estado final de los vanos amarrados del paso 11.

### 3.2 Selección correcta del viento para la ruta CFE

**La ecuación aerodinámica general NO reproduce por sí sola las presiones CFE dependientes del claro.** Para reproducir esas tablas se activa explícitamente `modelo_presion_cfe=True`. La pantalla `interfaz/mostrar_corridas_cfe_documentadas.py` ya pasa ese parámetro al coordinador; en cambio, una invocación directa de `ejecutar_corridas_cfe_por_vano()` conserva `modelo_presion_cfe=False` como valor predeterminado y **no utiliza** las presiones tabuladas salvo que el llamador active la opción.

Para la tabla registrada de CFE 05 00 03 (viento regional de 120 km/h):

| Claro horizontal `L_i` | Presión máxima tabulada | Carga lineal sobre el conductor |
|---:|---:|---|
| 50 m | 414 Pa | `414·D/1000` kN/m |
| 100 m | 386 Pa | `386·D/1000` kN/m |
| 150 m | 368 Pa | `368·D/1000` kN/m |
| 200 m | 355 Pa | `355·D/1000` kN/m |
| 300 m | 337 Pa | `337·D/1000` kN/m |

`presion_cfe_por_claro(L_i, velocidad_kmh)` devuelve presión en Pa para **120 km/h (máximo)** o **109 km/h (reducido)**, además de cero sin viento. Interpola linealmente entre claros documentados de **5 a 300 m**; **no extrapola** ni acepta otras velocidades. La presión ya incorpora el coeficiente CFE del conductor: **no se debe volver a multiplicar por `Cd` ni por `rho·V²/2`**. La carga para cada vano la aplica `calcular_cargas_transversales_por_vano()`.

En la ruta CFE, las hipótesis de clima y el valor de viento reducido suministrado deben ser **compatibles con la tabla seleccionada**. Si se activa el modo tabulado para una velocidad distinta de las documentadas (excepto viento cero), el módulo rechaza el cálculo; no debe sustituirse en silencio por la fórmula general.

## 4. Recorrido específico: generación y verificación de tablas CFE

Entrada pública: `motor_general.ejecutar_modulo("cfe", ...)` → `tension_tendido/ejecutar_corridas_cfe_documentadas.py::ejecutar_corridas_cfe_por_vano`.

| Etapa | Operación | Función responsable |
|---|---|---|
| **CFE-1** | Seleccionar propiedades iniciales y finales, con `EA_inicial`, `EA_final`, `alpha_inicial`, `alpha_final`, peso, diámetro y rotura | `seleccionar_propiedades_cfe_07_ft_01` |
| **CFE-2** | Construir los cinco estados: inicial 0 °C sin viento 33 % RTS; final 16 °C sin viento 20 %; final 0 °C sin viento 25 %; final −10 °C viento reducido + hielo declarado 45 %; final 0 °C viento máximo 45 % | `construir_hipotesis_cfe` |
| **CFE-3** | Determinar `H_50` final: `U(H)=max(T_max/T_lim, H_max/H_lim_documentado)` cuando aplique límite horizontal; buscar la **mayor H factible**, incluso si `U(H)` no es globalmente monótona | `calcular_tablas_cfe_inicial_final.py::calcular_parametro_cfe_desde_limites` |
| **CFE-4** | Calcular la referencia final y ajustar longitudes naturales a la distribución inicial del tendido continuo, después fijarlas por vano | `ejecutar_corridas_cfe_documentadas.py::_ajustar_referencia_final_multivano` y `_longitudes_de_tendido_continuo` |
| **CFE-5** | Acoplar referencia inicial y final por igualdad de **tracción máxima del estado extremo −10 °C**, con propiedades distintas por condición; buscar raíz y rechazar si no converge | `obtener_referencia_inicial_desde_extremo` |
| **CFE-6** | Verificar además 33 % RTS en estado inicial a 0 °C, así como los límites de tensión total/horizontal que correspondan | `ejecutar_corridas_cfe_por_vano` |
| **CFE-7** | Recalcular **cada vano real** a cada temperatura e hipótesis, `P_50=H_50/w`, reportar `H_i`, `T_max,i`, flecha, lateral y residuo | `calcular_tablas_cfe_inicial_final.py::calcular_tablas_inicial_final` |
| **CFE-8** | Comparar con criterios CFE adicionales cuando exista información geométrica y estructural completa | `verificaciones/verificar_restricciones_documentadas_cfe.py`, `verificaciones/evaluar_requisitos_cfe_por_vano.py` |
| **CFE-9** | Generar PDF CFE sin recalcular el motor | `salidas/PDF/generar_pdf_corrida_cfe.py::generar_pdf_corrida_cfe` |

**Distinciones críticas:**
- El parámetro `P_50=H_50/w` es **salida** del cálculo de referencia en la ruta documentada, no una lectura oculta de una tabla ENEE/CFE. El claro regla, si se presenta, es informativo y **no** reemplaza la geometría de los vanos reales.
- Los límites `TH1/TH2` de cabecera CFE, cuando están disponibles para viento regional documentado, son **horizontales** y se comprueban aparte de `T_max <= 0.45·RTS`.
- La densidad de hielo de ensayo por defecto en esa ruta es **913 kg/m³**, explícitamente marcada como dato del ensayo; viento reducido y espesor de hielo pueden ser cero **si el caso de estudio así lo declara**.
- El acoplamiento inicial/final por estado extremo **no predice creep** ni prueba identidad con SAGSEC. No se inventan elongaciones permanentes.
- `tension_tendido/cfe_claro_diseno_y_claros_regla.py` constituye una ruta de **comparación alternativa**: admite referencia de flecha final a 50 °C y `epsilon_permanente` explícita. No es automáticamente la ruta de ejecución CFE anterior.

## 5. Recorrido alternativo: BVP tridimensional con viento sobre tangente local

Usado cuando no basta representar el viento como carga vectorial uniforme transversal al vano. Este solucionador trabaja **por vano fijo** y se emplea también dentro de las rutas de red compatibles.

| Paso | Formulación | Código |
|---|---|---|
| **BVP-1** | Hallar el estado de referencia sin viento y su longitud natural `S_n,ref` | `catenaria/resolver_catenaria_exacta.py::resolver_catenaria`; `cambio_estado/resolver_cambio_de_estado.py::longitud_natural` |
| **BVP-2** | `S_n(theta)=S_n,ref[1+alpha·Δtheta+epsilon_perm]` | `catenaria/resolver_cable_tridimensional_bvp.py::resolver_cable_no_lineal` |
| **BVP-3** | Tangente `t=T/|T|`; componente normal del viento `V_perp=V-(V·t)t` | `resolver_cable_tridimensional_bvp.py::_aerodinamica` |
| **BVP-4** | `q_a = (rho·Cd·D/2000)·|V_perp|·V_perp` en kN/m; sumar peso `q_g=(0,0,-w)` | `_aerodinamica` |
| **BVP-5** | Ecuaciones en longitud material natural térmica `s`: `dr/ds=(1+|T|/EA)t` y `dT/ds=-(1+|T|/EA)(q_g+q_a)` | `resolver_cable_no_lineal` / función interna `ecuaciones` |
| **BVP-6** | Condiciones de frontera `r(0)=A`, `r(S_n)=B`; resolver `solve_bvp` | `resolver_cable_no_lineal` / `fronteras` |
| **BVP-7** | Integrar fuerzas y comprobar equilibrio `F_A+F_B-integral(q ds_real)=0`, error geométrico de frontera y residual de EDO | `resolver_cable_no_lineal` |
| **BVP-8** | Refinar `T_max` sobre el interpolador numérico, no solo en los puntos de salida | `resolver_cable_no_lineal` |
| **BVP-9** | Repetir estados, calcular extremos geométricos y calidad numérica | `hipotesis_climaticas/evaluar_estados_climaticos_bvp_3d.py::ejecutar_barrido_no_lineal_3d` |

**No confundir:** `hipotesis_climaticas/evaluar_estados_climaticos_catenaria_3d.py::ejecutar_barrido_3d` usa catenaria exacta **bajo carga uniforme** y viento normal al eje del vano; `ejecutar_barrido_no_lineal_3d` usa viento perpendicular a la tangente **local del cable**. Ambos dan resultados tridimensionales, pero no emplean la misma ley aerodinámica.

## 6. Recorrido alternativo: red mecánica y secciones deslizantes

La topología exige tipos de conexión declarados: `ANCLAJE`, `FIJA`, `SUSPENSION` o `DESLIZANTE`. Declarar una clase no significa que todos los modelos sepan resolverla.

| Paso | Condición matemática/física | Archivo y función |
|---|---|---|
| **RED-1** | Leer puntos, vanos, circuitos, secciones, conexiones por extremo y altura de amarre | `entradas/importar_red.py::leer_red_excel`; `entradas/importar_hipotesis_red.py` |
| **RED-2** | Construir nodos y aristas, validar conectividad y tipos | `calculos/modelo_red.py::RedMecanica.desde_registros`, `.validar`, `.secciones` |
| **RED-3** | Fijar longitudes naturales de referencia por vano o total de sección, según **tipo de unión real declarado** | `calculos/ensamblador_global.py::_preparar`; `tension_tendido/resolver_seccion_deslizante_ideal.py::resolver_seccion_deslizante` |
| **RED-4** | En guía **ideal deslizante**, conservar `sum S_n,i` e imponer igualdad de magnitudes de tracción a ambos lados, sin fricción | `resolver_seccion_deslizante` |
| **RED-5** | Para nodos trasladables con rigidez documentada, resolver equilibrio de fuerzas nodales mediante residuales y `least_squares` | `calculos/ensamblador_global.py::resolver_equilibrio_global` |
| **RED-6** | Evaluar cada hipótesis completa, flechas, tracciones y acciones XYZ por apoyo | `calculos/hipotesis_red.py::calcular_hipotesis_red`; `calculos/barrido_global.py::barrido_red_global` |

**Limitaciones estrictas:** el ensamblador global actual no resuelve una suspensión con grapa real de comportamiento general, rotaciones del poste, retenidas ni cimentación no lineal. Las configuraciones fuera de su dominio se rechazan; **no** deben reportarse como verificadas. `SUSPENSION` y `DESLIZANTE` no son físicamente sinónimos.

## 7. Cargas adicionales, verificaciones, terreno y memorias

| Aspecto | Cálculo/control | Responsable |
|---|---|---|
| Hielo | `w_h = pi·[(D/2+e)^2-(D/2)^2]·rho_h·g/1000` (D,e en m), `D_viento=D+2e` | `hipotesis_climaticas/generar_barrido_de_temperatura_viento_hielo.py::_peso_hielo_kN_m` y `EvaluadorVanosAmarrados.evaluar_estado_con_hielo` |
| Envolventes | Extremos por hipótesis completa sin mezclar componentes de estados diferentes | `verificaciones/envolventes_3d.py` |
| Residuos y auditoría | Equilibrio, coherencia de cargas, convergencia | `verificaciones/auditoria_cargas.py`, `resumir_calidad_numerica_bvp.py` |
| Capacidad de conductor | Comparación de tensión máxima y resistencia de rotura documentada | `verificaciones/comparar_tension_con_rotura_acsr.py`; `verificar_limites_documentados_de_tension.py` |
| CFE y despejes | Restricciones de tablas, separaciones, espacios verticales/horizontales cuando hay insumos suficientes | `verificaciones/verificar_restricciones_documentadas_cfe.py` |
| Terreno | Muestreos de DEM/GeoTIFF, conversión EPSG y libramiento **preliminar** | `topografia/modelo_terreno.py::extraer_terreno_apoyos`, `::calcular_libramientos_muestreados` |
| Memoria Etapa 1 | Informe y anexos desde tablas existentes | `salidas/PDF/generar_pdf_etapa_1.py::generar_pdf_etapa_1` |
| Memoria CFE | Resumen inicial/final, tablas, figuras y controles | `salidas/PDF/generar_pdf_corrida_cfe.py::generar_pdf_corrida_cfe` |
| PDF coordinado | Reúne generadores registrados; **no ejecuta cálculo** | `salidas/PDF/coordinar_pdf.py::generar_memoria_pdf` |

## 8. Rutas de ejecución y reglas de arquitectura

```text
Streamlit: app.py -> main.py
                    -> motor_general.py
                       |-> "conductores" -> ejecutar_analisis_integral()
                       |                   -> resolver_seccion_regulacion()
                       |                   -> EvaluadorVanosAmarrados
                       |                   -> resolver_cambio_estado + resolver_catenaria
                       |                   -> tablas / barrido / PDF
                       |
                       |-> "cfe" -> ejecutar_corridas_cfe_por_vano()
                       |            -> cinco hipótesis y referencias inicial/final
                       |            -> longitudes naturales por vano y tablas
                       |
                       |-> calcular_hipotesis_red()
                       |            -> modelo_red + ensamblador_global (dominio limitado)
                       |
                       `-> "estructuras" -> Módulo 2 (independiente)
```

- Los cálculos de conductor **no** importan cálculos del Módulo 2; el `motor_general.py` coordina los productos de ambos.
- Las funciones físicas se ubican en `catenaria/`, `cambio_estado/`, `tension_tendido/` y `calculos/`, según su responsabilidad. Los archivos de `interfaz/` deben limitarse a captura/presentación; `salidas/PDF/` no recalcula tensiones.
- `entradas/hipotesis_tendido.py::leer_hipotesis_tabla` valida la tabla independientemente de Streamlit. El adaptador Excel de regulación llama a la implementación canónica interna del módulo; no realiza una llamada de vuelta al coordinador.
- Las propiedades de catalogación ACSR se comparten con `comun/`. El archivo `validaciones/validar_datos_fisicos.py` reexporta validadores compartidos para compatibilidad; **no crea otra física**.
- El historial del código se conserva en Git. No borrar funciones de referencia, rutas no usadas en la pantalla principal o ensayos por el solo hecho de no tener consumidor directo en `main.py`.

### Motor único operativo del Módulo 1

La ruta principal tiene **un único coordinador**:
`motor_general.ejecutar_modulo("cfe")` →
`Analisis_mecanico_conductores/motor_conductores.py::ejecutar_motor_conductores` →
`ejecutar_corridas_cfe_por_vano` → evaluadores, catenaria,
compatibilidad, cinco hipótesis y tablas.

- El flujo principal usa **presiones tabuladas CFE por claro**; no ofrece
  cuatro procedimientos de cálculo elegibles por separado en `main.py`.
- Las **cinco hipótesis CFE son restricciones** aplicadas a la misma
  ejecución, no motores matemáticos alternativos.
- Todos los estados de **cada condición** (inicial/final) conservan sus
  longitudes naturales fijadas por vano durante el barrido climático.
- La ruta ordinaria usa **una misma longitud natural de referencia por vano**
  en las condiciones inicial y final a 50 °C: **creep adicional = 0**.
  En cada condición se conservan sus E y α originales CFE, se verifican
  las cinco hipótesis y se comprueba la compatibilidad con cada vano fijo.
  **No se fuerza la igualdad de tensiones extremas** ni se afirma modelar
  la evolución real del creep del ACSR. La antigua ruta de comparación
  por acoplamiento extremo permanece accesible en llamadas directas,
  pero no forma parte del motor único operativo.
- El BVP no lineal, la regulación general, el tendido inverso y el
  ensamblador global permanecen disponibles como implementaciones
  internas para sus pruebas y futura integración, **sin alterar ecuaciones**.
  La entrada ordinaria en `main.py` ya no los ofrece como recorridos
  independientes. No se han integrado todavía como un mismo modelo
  físico y estructural.

## 9. Ejecución y pruebas

Desde la raíz del repositorio:

```bash
python -m pip install -r requirements.txt
streamlit run app.py
python -m unittest discover -s tests -p 'test_*.py' -v
python -m unittest discover -s Analisis_mecanico_conductores/pruebas -p 'test_*.py' -v
python tools/auditar_codigo.py
```

Los casos de CFE están entre las regresiones de `tests/`; los ensayos específicos de conductor se encuentran en `Analisis_mecanico_conductores/pruebas/`. Las pruebas evitan cambios accidentales de API, compatibilidad y resultados, pero **no reemplazan** la revisión técnica independiente de cualquier proyecto construido.

## 10. Alcance pendiente, sin alterar el avance actual

1. Continuar las validaciones de casos reales y documentación de tolerancias/hipótesis con fuentes.
2. Distinguir explícitamente uso de las rutas convencionales, exactas y BVP para evitar comparar condiciones físicas diferentes.
3. Completar en el Módulo 2 las capacidades verificadas de postes, crucetas, aisladores, retenidas, anclajes y cimentación; integrarlas sin importaciones cruzadas.
4. No declarar creep modelado hasta contar con una ley constitutiva y parámetros validados. `E_inicial`, `E_final` o la igualdad de una tensión extrema no bastan por sí solos.
5. Reportar como preliminares las evaluaciones de topografía muestreada y de la red global fuera de su dominio físico completo.

**Regla de mantenimiento:** preservar ecuaciones y propiedades documentadas; modificar modelos solo con fundamento físico y regresiones de comparación. Refactorizar nombres, archivos o rutas no constituye por sí mismo una mejora mecánica.


### Remates intermedios y secciones de tendido

El Excel principal admite la columna `Remate` con valores `SI`/`NO`
(o `REMATE`/`PASO`). Sin columna se considera una única sección
entre primer y último apoyo, compatible con proyectos anteriores.
Si existe la columna, no se aceptan remates intermedios vacíos: deben
especificarse explícitamente. Los extremos siempre son remates.

Ejemplo P1-P2-P3-P4-P5-P6 con P3 remate:
`P1(SI), P2(NO), P3(SI), P4(NO), P5(NO), P6(SI)`.
El motor identifica `S1=P1..P3` y `S2=P3..P6`, calcula una referencia
de tendido para **cada sección** y evalúa luego los vanos fijados
individualmente con las cinco hipótesis CFE y creep adicional cero.
La misma estructura física P3 es frontera de ambas secciones, pero no
transfiere longitud natural entre ellas. La memoria PDF agrupa las
secciones sin mezclar su tensión de tendido. Todavía no se certifica
la capacidad estructural del poste ni sus retenidas.


### Vista superior de apoyos y vanos

La interfaz principal vuelve a mostrar el trazado en planta antes de
las hipótesis climáticas. Dibuja los puntos X/Y del Excel, etiquetas de
apoyos, claros horizontales y colores por sección de tendido; identifica
remates sin inferir retenidas. El dibujo usa exactamente la segmentación
`dividir_secciones_por_remates` del motor CFE y no modifica resultados
mecánicos.


### Memoria unificada de una línea con múltiples secciones

La ruta principal genera **un solo informe de la línea completa**: portada,
resumen y extremos globales, identificación de cada sección entre remates,
referencias de tendido independientes por sección, control de las cinco
hipótesis para cada sección, longitudes fijadas de todos los vanos,
perfiles por vano y anexos conjuntos por condición. No concatena memorias
independientes y no mezcla las tensiones de referencia de distintas secciones.
