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

comun/         Catálogos ACSR compartidos y validación física única
Analisis_mecanico_conductores/calculos/    Modelo de red, equilibrio, hipótesis y barrido global
entradas/      Lectura Excel y validación compartida (sin interfaz ni catálogos duplicados)
tests/         Pruebas de integración y regresión
tools/         Auditoría estática reproducible
```

**Reglas:** los Módulos 1 y 2 no se importan entre sí. `motor_general.py` distribuye las llamadas. Un catálogo común tiene una implementación única en `comun/`. No añadir lógica de cálculo en adaptadores de compatibilidad. El paquete histórico `analisis/` fue migrado y eliminado.

## Funcionalidades y límites

- **Módulo 1 — Conductores:** catenaria 3D, cambios de estado, vanos individuales después del amarre, hipótesis CFE, controles y memorias PDF. No es una certificación ni una ley predictiva validada de creep.
- **Módulo 2 — Estructuras:** las rutinas históricas de geometría, cargas, apoyos, postes, retenidas y cimentación están en `Analisis_mecanico_estructuras/calculos/`. El motor inicial calcula fuerzas preliminares; debe emitir **NO VERIFICABLE** donde falten capacidades resistentes documentadas. No constituye una verificación estructural integral.
- **Red global:** `Analisis_mecanico_conductores/calculos/` contiene `modelo_red.py`, `ensamblador_global.py`, `hipotesis_red.py` y `barrido_global.py`. Los prototipos de conectividad y equilibrio se conservan sin cambios matemáticos y no certifican el diseño estructural.

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
python -m compileall -q Analisis_mecanico_conductores Analisis_mecanico_estructuras comun entradas motor_general.py main.py
```

Las pruebas automáticas de GitHub incluyen una regla explícita de ausencia de importaciones cruzadas entre módulos. Consulta `ayuda/METODOLOGIA_MECANICA.md` para la metodología y los límites; el historial de migración se conserva en Git.

**La cantidad de archivos no es un criterio de calidad:** las pruebas, catálogos trazables, cálculos históricos útiles y ejemplos se conservan. Solo se retiran duplicaciones y rutas obsoletas después de comprobar consumidores y equivalencia.
