# Ayuda técnica

Esta carpeta conserva **una sola explicación metodológica vigente**, las referencias normativas y un ejemplo de ejecución. No almacena versiones antiguas o repetidas de los mismos documentos.

- [Metodología mecánica, referencias y límites](METODOLOGIA_MECANICA.md): catenaria 3D, compatibilidad, cambio de estado, tendido inverso, comparación Checa, red global, alcance y advertencias
- [Criterios documentados CFE 2014](criterios_documentados_cfe_2014.md): referencias de las tablas, casos y restricciones; conservar advertencias de extracción y no trasladar automáticamente capacidades a ENEE
- `ejemplo_barrido_3d.py`: caso de prueba ilustrativo con propiedades **sintéticas**, no aptas para dimensionamiento

Para verificar dependencias, rutas y sintaxis utilizar `python tools/auditar_codigo.py` y el flujo automático `.github/workflows/pruebas_motor.yml`. Se eliminó el antiguo verificador local porque buscaba carpetas que ya no existen.

El historial de la migración de `analisis/` y las salidas PDF permanece en Git. La estructura vigente se describe en el [README principal](../README.md).
