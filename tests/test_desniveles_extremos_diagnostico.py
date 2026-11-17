"""Diagnóstico numérico de vanos con desniveles severos; no forzar cumplimiento."""
import unittest
import pandas as pd
from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import (
    seleccionar_propiedades_cfe_07_ft_01, ejecutar_corridas_cfe_por_vano
)

class TerrenoExtremo(unittest.TestCase):
    def test_vanos_desnivelados_mensaje_diagnostico(self):
        puntos=pd.DataFrame({
            "Punto":["P1","P2","P3","P4","P5","P6"],
            "X":[0.,50.,120.,240.,390.,690.],
            "Y":[0.,0.,0.,0.,0.,0.],
            "Altitud":[100.,125.,92.,155.,110.,185.],
            "Poste":["PC-40"]*6,
            "Altura_Amarre_m":[9.5,10.5,9.,11.5,10.,12.],
            "Espacio Retenida":["SI"]*6,
        })
        ini,fin=seleccionar_propiedades_cfe_07_ft_01("RAVEN")
        try:
            resumen,tabla=ejecutar_corridas_cfe_por_vano(
                puntos,ini,fin,viento_max_kmh=120.,
                viento_reducido_kmh=0.,hielo_mm=6.,
                temperaturas_C=[-10.,0.,16.,20.,50.],
                Cd=1.,rho_kg_m3=1.225,
            )
        except Exception as exc:
            raise AssertionError(
                f"Diagnóstico de prueba extrema: {type(exc).__name__}: {exc}"
            ) from exc
        self.assertEqual(int(resumen["Número de vanos"].iloc[0]),5)
        self.assertFalse(tabla.empty)
