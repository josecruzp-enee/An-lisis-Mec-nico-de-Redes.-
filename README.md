# Análisis mecánico de redes de distribución

Aplicación Streamlit para cálculo mecánico de conductores y desarrollo posterior de verificaciones de estructuras de soporte.

## Estado de los módulos

- **Módulo 1 — Conductores:** catenaria exacta, compatibilidad termoelástica, tendido ideal continuo anterior al amarre, vanos fijados independientemente después del amarre, hipótesis climáticas y memoria PDF. Es un módulo funcional con validación numérica parcial frente a referencias CFE, **no una certificación de diseño**.
- **Módulo 2 — Estructuras:** desarrollo y validación pendiente. No confundir los cálculos preliminares de postes y retenidas ya existentes con una verificación estructural completa.
- Módulos posteriores: cadenas y grapas, poste con grados de libertad y red completa.

## Ejecución

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

El punto de entrada `app.py` invoca `main.py`. Los módulos CFE y la interfaz mecánica se encuentran bajo `Analisis_mecanico_conductores/`.

## Organización y compatibilidad

- `Analisis_mecanico_conductores/`: implementación específica del análisis de conductores.
- `calculos/`, `entradas/`: funciones de red, integración y estructuras; parte de su contenido son rutas históricas.
- `analisis/calculos/`: implementaciones de cálculos preliminares de soporte usadas por interfaces antiguas.
- `salidas/PDF/`: generadores de memorias que consumen resultados calculados, sin sustituir el motor.
- `tests/` y `Analisis_mecanico_conductores/pruebas/`: regresiones numéricas y pruebas de compatibilidad.
- `ayuda/`: documentación del modelo, decisiones y límites.

Las rutas antiguas se mantienen deliberadamente si son importadas por interfaces o tests. **No introducir una segunda implementación** en un archivo de compatibilidad; modificar la implementación canónica indicada en el docstring.

## Verificación antes de modificar el motor

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
python -m unittest discover -s Analisis_mecanico_conductores/pruebas -p 'test_*.py' -v
python -m compileall -q Analisis_mecanico_conductores analisis calculos entradas salidas main.py
python tools/auditar_codigo.py
```

El workflow de GitHub Actions ejecuta esas comprobaciones en `main` y en las solicitudes de cambio. Además informa importaciones y variables sin uso con Ruff; los archivos de compatibilidad pueden reexportar símbolos deliberadamente.

## Límites actuales

El acoplamiento entre referencias inicial/final no implementa una ley predictiva validada de creep. No está demostrada la capacidad estructural integral de postes, crucetas, herrajes, retenidas y cimentaciones. El reporte CFE verifica las restricciones implementadas, no todas las exigencias de una obra.

## Preparación del Módulo 2

Separar demanda mecánica del conductor (fuerzas XYZ y momentos en cada apoyo) de la capacidad resistente documentada de cada componente. La verificación se hará por hipótesis y por elemento: poste, cruceta, aislador, retenida y cimentación. Los archivos preliminares existentes no deben considerarse aprobados sin auditoría individual.

Para la trazabilidad de la depuración, consultar `ayuda/DEPURACION_PRE_MODULO_2.md`.
