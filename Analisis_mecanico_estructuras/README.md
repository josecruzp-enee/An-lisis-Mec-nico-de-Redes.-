# Módulo 2 — Análisis mecánico de estructuras

**Estado: implementación histórica migrada, en fase preliminar.**

## Organización

- `entradas/norma_postes.py`: fichas, identificación y geometría de postes.
- `calculos/`: once implementaciones trasladadas íntegramente de `analisis/calculos/` y el cálculo preliminar de fuerzas nodales.
- `motor.py`: coordina el cálculo estructural heredado para apoyos nivelados y tensión prescrita.
- `salidas/resultados.py`: expone las tablas ya calculadas sin alterar fuerzas ni declarar cumplimiento.

La interfaz llama a `motor_general.ejecutar_modulo("estructuras", ...)`. **Este módulo no importa el código del Módulo 1**; cuando posteriormente utilice sus resultados deberá recibirlos a través del coordinador.

## Alcance limitado

El motor original conserva su clasificación `PRELIMINAR`; las verificaciones de poste, cimentación y retenidas no pueden declararse completas sin datos normativos y materiales documentados. Los algoritmos históricos de perfil incluyen aproximaciones que deben auditarse antes de emplearse como libramientos de diseño. Sus ecuaciones se preservaron durante la migración.

## Desarrollo pendiente

Contrato de fuerzas y momentos XYZ por hipótesis, capacidades verificadas de poste y cruceta, grapas/aisladores, retenidas y anclajes, cimentación y memoria PDF independiente, con regresiones de escenarios críticos.
