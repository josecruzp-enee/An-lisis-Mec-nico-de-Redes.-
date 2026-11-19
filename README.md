# Análisis mecánico de redes de distribución

Aplicación de ingeniería en Python y Streamlit. **El cálculo del Módulo 1 es funcional; los cálculos estructurales del Módulo 2 todavía son preliminares.**

## Arquitectura modular

```text
app.py → main.py → motor_general.py
                         ├── Analisis_mecanico_conductores/
                         │   ├── entradas/
                         │   ├── tension_tendido/, catenaria/, cambio_estado/, ...
                         │   ├── interfaz/
                         │   └── salidas/PDF/
                         └── Analisis_mecanico_estructuras/
                             ├── entradas/
                             ├── calculos/
                             ├── motor.py
                             └── salidas/

comun/         Catálogo físico compartido entre módulos, sin dependencia cruzada
calculos/      Algoritmos globales y de red todavía en desarrollo
entradas/      Interfaz y archivos de entrada comunes y de red
tests/         Pruebas de integración y regresión
tools/         Auditoría estática reproducible
```

**Reglas:** los Módulos 1 y 2 no se importan entre sí. `motor_general.py` distribuye las llamadas. Un catálogo común tiene una implementación única en `comun/`. No añadir lógica de cálculo en adaptadores de compatibilidad. El paquete histórico `analisis/` fue migrado y eliminado.

## Funcionalidades y límites

- **Módulo 1 — Conductores:** catenaria 3D, cambios de estado, vanos individuales después del amarre, hipótesis CFE, controles y memorias PDF. No es una certificación ni una ley predictiva validada de creep.
- **Módulo 2 — Estructuras:** las rutinas históricas de geometría, cargas, apoyos, postes, retenidas y cimentación están en `Analisis_mecanico_estructuras/calculos/`. El motor inicial calcula fuerzas preliminares; debe emitir **NO VERIFICABLE** donde falten capacidades resistentes documentadas. No constituye una verificación estructural integral.
- **Red global:** algoritmos para conectividad, catenarias de cable y equilibrio en `calculos/`. Algunos son prototipos de investigación y no están certificados para diseño.

## Ejecución

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## Verificación

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
python -m unittest discover -s Analisis_mecanico_conductores/pruebas -p 'test_*.py' -v
python tools/auditar_codigo.py
python -m compileall -q Analisis_mecanico_conductores Analisis_mecanico_estructuras comun calculos entradas motor_general.py main.py
```

Las pruebas automáticas de GitHub incluyen una regla explícita de ausencia de importaciones cruzadas entre módulos. Consulta `ayuda/METODOLOGIA_MECANICA.md` para la metodología y los límites; el historial de migración se conserva en Git.

**La cantidad de archivos no es un criterio de calidad:** las pruebas, catálogos trazables, cálculos históricos útiles y ejemplos se conservan. Solo se retiran duplicaciones y rutas obsoletas después de comprobar consumidores y equivalencia.
