# Validación y límites

Ejecutar `python -m unittest discover -s tests -v` desde la raíz.
No requiere red, Streamlit ni GitHub. Usa NumPy/Pandas/OpenPyXL/Matplotlib.

Casos cubiertos: catenaria nivelada/desnivelada y con carga lateral, extremos
exactos, longitud, reacciones, equilibrio global, carga pequeña, entradas no
finitas, vano vertical rechazado, compatibilidad identidad/calor/carga,
cuadratura 64 contra 128, sección ideal multivano, mínimo de despeje analítico,
giros 0/5/30/60/90°, remates, retenida a 3 m, cable flojo, compresión inducida,
rigidez singular, importación Excel, proyecto multicaso con alternativas,
serialización, capacidades faltantes, falla gobernante y selección económica.

Los valores del piloto son sintéticos. Estas pruebas verifican matemáticas y
contratos; no validan un poste real ni certifican la especificación del cable.
Antes de producción se requieren ejemplos independientes publicados y aprobación
de modelos/capacidades por especialidad. Un resultado NO VERIFICABLE es correcto
cuando la información no permite justificar resistencia, anclaje o cimentación.

## Ejecución en esta rama

21 pruebas automatizadas pasaron. Se comprobó además compilación e importación
de todos los módulos, apertura de ambas entradas Streamlit mediante AppTest,
render de tablas/perfil con un caso sintético y generación/inspección de PDF.
No se probó despliegue Streamlit Cloud ni datos de un proyecto real del propietario.
