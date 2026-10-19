# Auditoría y ruta de desarrollo

Base auditada: `cb6a561c0ae3ad77fb2820caba6342a57541dd0e`, rama `main`.
Implementación aislada: `desarrollo/analisis-mecanico-integral`.
La instrucción del propietario de implementar en rama sustituye la instrucción
inicial del adjunto de limitar la primera entrega a planificación.

## Hallazgos y tratamiento

| Archivo | Hallazgo original | Tratamiento |
|---|---|---|
| perfil.py | Catenaria nivelada aplicada como parábola; sin empotramiento; despeje 0 aprobaba | Catenaria exacta desnivelada, mínimo analítico, alturas explícitas y criterio opcional |
| engine.py | Peso combinado con viento enviado como fuerza horizontal; faltaba tracción | Adaptador Excel hacia fuerzas exactas; sin datos no calcula ni aprueba |
| cargas_tramo.py | Multiplicaba peso por fases pero no viento | Mismo número de cables para ambas cargas; velocidad normal al cuadrado |
| fuerzas_nodo.py | Viento en azimut global, podía recibir peso resultante | Auxiliar restringido a viento transversal; motor exacto en cargas_espaciales |
| norma_postes.py | Ruptura usada como admisible; desconocidos 9999 kN; PM-40 tratado como concreto | Capacidad admisible desconocida representada con NaN; alias madera/concreto eliminado |
| mecanica.py | POSTES inexistente; capacidades artificiales | Adaptador seguro y validación de fracción/FS; catálogo sin modificar |
| retenidas.py | Ángulo 45° y equilibrio idealizado | Se conserva auxiliar identificado; ruta nueva exige coordenadas y rigidez |
| equilibrio_poste.py | Recortaba fuerzas negativas a cero | Conserva signo; nuevo equilibrio unilateral 3D |
| cimentacion.py | 50 kN para cualquier suelo; R=M/d aprobaba | Indicador sin aprobación; verificaciones parciales con capacidades explícitas |
| decision_soporte.py | Autosoportado por falta de espacio; retenida podía aprobar sin poste | Ruta heredada no aprueba; alternativas se evalúan por caso y componente |
| geometria.py | Redondeo antes del cálculo | Se conserva precisión de longitudes/azimutes; clasificación geométrica no diseña retenidas |
| io_excel.py | Perdía mayúsculas de columnas de amarre y no convertía Altitud | Normalización y validación de etiquetas, coordenadas, duplicados |
| momento_poste.py | H*h y alturas supuestas; no excentricidad | Auxiliar histórico, fuera del motor de decisión; sustitución por r×F |
| exportacion_excel.py | Sólo algunas tablas | Exporta todas las tablas, trazabilidad y paquete JSON completo |
| reporte_pdf.py | Imports de símbolos inexistentes; fórmulas no conectadas con motor | Adaptador hacia memoria paginada |
| catalogos.py | Procedencia y versiones incompletas; faltan EA/alpha/interacciones | Se conserva exactamente; no se agrega un Flicker ficticio |
| app.py | Parámetros fijos invisibles | Controles explícitos y modo JSON; datos faltantes visibles |
| datos_proyecto.py | Formulario alternativo no usado por app | Conservado, sin introducir dependencia de UI en motor |
| unidades.py | Conversiones existentes | Conservado; nuevos módulos documentan unidades explícitas |
| mapa_proyecto.py / Ayuda | Utilidades de inventario | Sin efectos en cálculo |

## Estado de las fases

| Fase | Implementado y comprobable | Pendiente para cerrar producción |
|---|---|---|
| 0 Auditoría | Inventario, consumidores públicos y fallas principales | Auditoría independiente del dominio |
| 1 Ecuaciones | Deducciones y dominios en ECUACIONES.md | Referencias bibliográficas con páginas verificadas |
| 2 Datos | Contratos de nodo, vano, conductor, clima, combinación; JSON versionado por motor | Topología con suspensión y secciones móviles; migraciones de esquema |
| 3 Conductor | Catenaria 3D bajo q uniforme; compatibilidad elástica/térmica; creep impuesto | Leyes multicomponente y fluencia dependiente del tiempo; suspensión acoplada |
| 4 Cargas | Viento transversal, peso, hielo explícito, acciones adicionales, r×F, envolventes | Catálogo normativo de combinaciones, rotura dinámica, arrastre dependiente de tangente |
| 5 Estructuras | Modelo elástico reducido con cables unilaterales; chequeos de capacidad por componente | Secciones reales por material, P-delta, fisuración, pandeo, conexiones y geotecnia no lineal |
| 6 Decisión | Tres estados, todos los casos y costos completos | Validación con alternativas reales que satisfagan TODOS los controles |
| 7 Integración | Excel preservado; JSON avanzado; UI y exportación | Prueba del propietario con sus proyectos reales |
| 8 Validación | Pruebas físicas, numéricas, importación y regresión | Casos publicados independientes y revisión ENEE |
| 9 Memorias | PDF, Excel y JSON reproducible | Memoria normativa aprobada por responsable |

**No se declara terminado el sistema profesional integral.** Las comprobaciones
específicas de estabilidad, resistencia local y suelo no se sustituyen por
capacidades inventadas: bloquean la aprobación. Actualmente las alternativas
integrales permanecen NO VERIFICABLE (o NO CUMPLE cuando se demuestra una falla)
hasta completar esos modelos. No existe un interruptor para forzar CUMPLE.

## Orden de las siguientes implementaciones

1. Verificar fichas exactas: cable ACSR 477 y composición, propiedades inicial/final,
   temperatura y tensión de tendido, criterio climático y fuentes.
2. Definir sección real del poste y modelo de material; unidades y curvas de ensayo.
3. Implementar resistencia local, estabilidad y flexocompresión específica junto
   con pruebas de ejemplos independientes; actualizar resistencia_postes y sus consumidores.
4. Implementar interacción suelo–poste con estudio geotécnico por punto;
   actualizar alternativas_estructurales, modelo de cimentación y memoria juntos.
5. Incorporar suspensión desplazable y compatibilidad de toda la sección.
   No usar el vano regulador como sustituto sin justificar sus hipótesis.
6. Incorporar norma/edición/cláusula verificadas en combinaciones y límites.
7. Validar proyecto real contra cálculo manual independiente, luego habilitar
   selección técnica/económica de alternativas completas.

## Datos del caso piloto

34.5 kV, trifásico, vanos de 40 m, terreno plano, giro de 90°, dos remates,
altura de amarre de prueba 10 m, poste de referencia 40 pies, anclaje a 3 m.
La altura de amarre, rigidez del poste, EA, alpha y H del JSON son **sintéticos**.
Peso, diámetro y RTS reproducen el catálogo heredado 477 MCM; su correspondencia
con Flicker no ha sido verificada. No se adoptan capacidades de 3/8 EHS como
admisibles sin fuente/factor y herrajes. El ejemplo debe quedar NO VERIFICABLE.

## Criterios de aceptación

- Ninguna entrada no finita, duplicada o incompleta genera aprobación.
- Identidades de extremos y equilibrio conservan tolerancias declaradas en pruebas.
- Cambio de estado reproduce identidad y sensibilidad física al calor/carga.
- Fuerzas y momentos conservan signo y caso gobernante.
- Rigidez singular o no convergencia produce error explícito, no resultado utilizable.
- Fuente, método, tipo de resistencia y unidades acompañan cada comparación.
- Toda alternativa cumple cada verificación en cada caso antes de comparar costos.
- El criterio de éxito final del propietario sigue pendiente hasta completar la
  justificación estructural y geotécnica de alternativas reales.
