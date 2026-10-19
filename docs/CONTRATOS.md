# Uso, contratos y mantenimiento

## Ejecutar

Python 3.10 o posterior. `python -m pip install -r requirements.txt`.
Interfaz: `streamlit run app.py`.
Pruebas: `python -m unittest discover -s tests -v`.

## Entrada Excel compatible

Columnas obligatorias: Punto, X, Y. Punto único; coordenadas UTM en metros.
Opcionales: Poste, Espacio Retenida, Altitud, Altura_Amarre_m, Altura_Poste_m,
Empotramiento_m. Espacio ausente no se convierte en SI. No convertir zona UTM
ni datum implícitamente; todos los puntos deben estar en el mismo sistema.

Para fuerzas/perfil se necesitan Altitud y Altura_Amarre_m (sobre terreno) o
Altura_Poste_m (longitud total) + Empotramiento_m. Si la longitud está en catálogo
puede omitirse Altura_Poste_m. Offset usado por adaptador: 0.10 m, hipótesis
explícita de interfaz histórica, no norma. Preferir altura medida.

La interfaz exige H de tendido. Temperaturas del formulario son entradas
editables. EA y alpha sólo se requieren si cambia temperatura/carga. El perfil
Excel dibuja exclusivamente tendido sin viento; el motor JSON calcula estados.
El criterio de despeje no se asume 0. Sin criterio, no se aprueba el despeje.

`ejecutar_todo` conserva claves: tramos, deflexiones, resumen, total_m,
cargas_tramo, fuerzas_nodo, nodos, retenidas, equilibrio, cimentacion,
momento_poste, decision, perfil. Añade advertencias y trazabilidad.
Las tablas sin cálculo muestran Estado/Motivo NO VERIFICABLE: consumidores
externos que exigían columnas numéricas aun sin datos deben atender el estado.

`analizar_perfil` conserva arrays y tabla_vanos; añade tensión de ambos apoyos.
fraccion_trabajo ya no tiene valor automático. Puede suministrarse explícitamente
para estudios de sensibilidad; H_kN tiene precedencia. No equivale a cambio de estado.

## Proyecto JSON integral

Ejemplo ejecutable: `ejemplos/piloto_477_sintetico.json`. NO usar sus valores
sintéticos como diseño real. Los importes, capacidades y fuentes no son supuestos
universales; el responsable debe incorporar los datos de su proyecto.

- `modelo_secciones`: exactamente `vanos_retenidos`.
- `nodos`: nombre, base_m=[X,Y,Z] de terreno.
- `conductores`: nombre, peso_kN_m, diametro_m, H_tendido_kN,
  temperatura_tendido_C, fuente. Opcionales EA_kN, alpha_por_C, RTS_kN,
  tension_admisible_kN, fuente_admisible. Tendido sin viento ni hielo.
- `vanos`: nombre, inicio, fin, amarre_inicio_m y amarre_fin_m (offsets respecto
  a base), conductor y cantidad. Para separación de fases y torsión real, usar
  un registro por fase con su propio offset; cantidad agrupa cables co-localizados.
- `estados`: nombre, temperatura_C, viento_ms, azimut_deg, fuente. Opcionales
  Cd, rho_kg_m3, hielo_m, densidad_hielo_kg_m3, deformacion_permanente.
- `combinaciones`: nombre, estado, fuente, metodo (servicio/resistencia/especial),
  factor_conductor y factor_adicional. Factores unitarios por defecto son
  identidad matemática; no constituyen una combinación normativa.
- `acciones_adicionales`: nodo, estado, posicion_m (local), fuerza_kN,
  momento_kNm (opcional), fuente. Usar para equipos, cargas de poste y construcción.
- `alternativas`: diccionario nodo → lista de alternativas. Cada una: nombre,
  capacidades_poste, cimentacion, opcional rigidez_6x6 y fuente_rigidez,
  espacio_retenidas, retenidas, costo_total, fuente_costo.
- Cada retenida: amarre_m, ancla_m en coordenadas locales del nodo, EA_kN,
  pretension_kN opcional, capacidades por cable/fijacion/herrajes/varilla/ancla/suelo.

Una capacidad tiene `valor`, `fuente`, `tipo` (admisible/diseno) y `metodo`.
Las unidades las fija el control, no las adivina del número. Ver ECUACIONES.md.
Flexocompresion puede recibir `{modelo: suma_lineal, fuente: ...}` si ese es
el criterio documentado. No reemplaza controles de estabilidad/material.

La rigidez 6×6 corresponde a [ux,uy,uz,rx,ry,rz] y las acciones conjugadas son
[Fx,Fy,Fz,Mx,My,Mz]. Debe representar el modelo reducido y geometría usados.
Los anclajes están fijos; movimiento del suelo requiere otro modelo.

## Responsabilidades de archivos

| Archivo | Responsabilidad / entradas → salidas |
|---|---|
| modelos_datos.py | Contratos y validación de propiedades |
| validacion_mecanica.py | Dominio numérico y topológico común |
| geometria_amarres.py | Longitud/empotramiento/altura → amarres |
| catenaria.py | Dos apoyos, q, H → cable, reacciones, longitud, mínimos |
| cambio_estado.py | Tendido y propiedades → H final y residual |
| cargas_espaciales.py | Clima y cable → q; acciones → vector 6D |
| retenidas_espaciales.py | K, cargas, geometría y EA → equilibrio unilateral |
| estados_limite.py | Demanda/capacidad/fuente → tres estados |
| resistencia_postes.py | Acciones/capacidades → controles de poste |
| anclajes.py | T/capacidades → controles de cada componente |
| alternativas_estructurales.py | Alternativas/casos → estados y elección económica |
| motor_integral.py | JSON → tablas, envolventes y trazabilidad |
| engine.py | Entrada Excel → contrato histórico seguro |
| memoria_calculo.py | Resultados → PDF, Excel y JSON |
| interfaz_integral.py | UI; único módulo nuevo que importa Streamlit |

## Cómo modificar con seguridad

1. Cambiar primero contrato y ecuación documentada; indicar unidades y límites.
2. Buscar consumidores con `rg 'nombre_funcion' .`.
3. Escribir prueba independiente (equilibrio, solución cerrada, ejemplo publicado).
4. Cambiar función pequeña con docstring; comentarios explican hipótesis y signos.
5. No redondear dentro del cálculo; redondear sólo presentación.
6. Ejecutar pruebas y validar importaciones antes de publicar la rama.
7. Toda fuente no disponible conserva NO VERIFICABLE. No usar 9999, infinidades,
   valores por defecto ficticios ni habilitar CUMPLE desde la interfaz.

El motor no depende de Streamlit. Las colecciones de resultados conservan datos
sin redondear. JSON incluye entrada y huella SHA-256; Excel incluye todas las
tablas y el JSON en segmentos concatenables. PDF es memoria legible resumida:
acompañarlo con JSON/Excel para reconstruir el proyecto completo.
