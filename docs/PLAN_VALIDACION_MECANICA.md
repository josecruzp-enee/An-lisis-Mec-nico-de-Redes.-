# Plan de validación mecánica — distribución aérea
Estado: especificación de desarrollo; no autoriza decisiones de construcción.

## Jerarquía de referencias
1. Manual de Obras ENEE 2011: requisitos oficiales aplicables al proyecto y construcciones normalizadas.
2. Especificaciones ENEE de materiales y postes: verificar edición y vigencia antes de mezclar catálogos.
3. NESC/IEEE C2, guías ASCE 74, CFE y bibliografía técnica: métodos complementarios, identificar supuestos y alcance.

## Contratos de cálculo propuestos
- Unidades internas: m, N, N/m, Pa, K; conversión única hacia kN y kgf para presentar.
- Conductor/estado: geometría XYZ, propiedades mecánicas verificadas, condición inicial (temperatura y tiro/flecha), combinaciones climáticas. Resuelve compatibilidad termomecánica y catenaria por vano/sección de tensión. Resultado: vectores de esfuerzo en cada extremo y perfil de despejes.
- Cargas por punto: se suman vectores de tensión en los puntos de amarre, peso y viento con direcciones físicas separadas. Resultado Fx,Fy,Fz,Mx,My,Mz para cada combinación, sin mezclar peso vertical en carga de planta.
- Estructuras: comprobar resistencia disponible de poste, flexión biaxial, interacción axial, cortante, torsión y servicio. Carga de ruptura != carga admisible.
- Retenidas: incluir coordenadas XYZ del ancla, tracción unilateral, puntos de fijación, rigidez/pretensión cuando corresponda, resistencia de cable/herrajes/ancla y reparto compatible. No fijar 45 grados para todos los puntos.
- Cimentación: resistencia lateral y deformación mediante parámetros geotécnicos informados. Nunca inventar capacidad del suelo.
- Decisión: CUMPLE / NO CUMPLE / NO VERIFICABLE; nunca convertir falta de datos o ausencia de anclaje en aprobación de autosoportado.

## Defectos de referencia observados en main
- fuerzas_nodo.py: calcula sólo cargas distribuidas; no incluye tensión longitudinal de conductores.
- engine.py: perfil calcula con fraccion_trabajo=0.20 y despeje_min_m=0.0.
- norma_postes.py: poste desconocido retorna 9999 kN.
- decision_soporte.py: AUTOSOPORTADO puede emitirse sin verificar capacidad.
- cimentacion.py: capacidad_suelo_kN=50.0 aplicada sin justificación geotécnica.
- mecanica.py: función H_max_poste_kN refiere POSTES no definido.

## Secuencia de implementación
1. Congelar referencia de main y crear pruebas de regresión físicas de tres nodos: tangente, giro 90° y remate; comprobar caso sin viento y con viento en varias direcciones.
2. Definir contratos de entradas/salidas y resolver estados de conductor; validar contra ejemplos independientes de la bibliografía.
3. Integrar esfuerzos vectoriales por apoyo; ensayar sumas de fuerzas y momentos con geometrías conocidas.
4. Incorporar retenidas y postes, fuerzas residuales y capacidades certificados.
5. Incorporar anclajes/cimentaciones con datos geotécnicos; bloquear si faltan.
6. Generar memorias, validar contra casos independientes y sólo entonces plantear fusión a main.

Ningún factor, estado climático, vano equivalente o capacidad de poste podrá adoptarse silenciosamente. Cada decisión debe trazarse a datos, regla ENEE o supuesto de ingeniería identificado.
