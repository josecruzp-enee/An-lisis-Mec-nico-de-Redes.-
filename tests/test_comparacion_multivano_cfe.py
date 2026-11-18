"""Ensayo real del ensamblador de sección continua ideal."""
import unittest
import pandas as pd

from Analisis_mecanico_conductores.tension_tendido.comparar_multivano_deslizante_cfe import (
    construir_red_deslizante_de_puntos,
    calcular_comparacion_multivano_final,
)
from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import (
    seleccionar_propiedades_cfe_07_ft_01,
)


class MultivanoCFEIntegrado(unittest.TestCase):
    def setUp(self):
        self.puntos=pd.DataFrame({
            "Punto":["P1","P2","P3"],
            "X":[0.,50.,100.],
            "Y":[0.,0.,0.],
            "Altitud":[0.,0.,0.],
            "Altura_Amarre_m":[10.,10.,10.],
        })

    def test_conectividad_anclajes_y_guias(self):
        red=construir_red_deslizante_de_puntos(self.puntos,"RAVEN")
        self.assertEqual(len(red.vanos),2)
        v=list(red.vanos.values())
        self.assertEqual(v[0].conexion_origen,"ANCLAJE")
        self.assertEqual(v[0].conexion_destino,"DESLIZANTE")
        self.assertEqual(v[1].conexion_origen,"DESLIZANTE")
        self.assertEqual(v[1].conexion_destino,"ANCLAJE")

    def test_ensayo_numerico_dos_vanos_simetrico(self):
        _,ficha=seleccionar_propiedades_cfe_07_ft_01("RAVEN")
        tabla=calcular_comparacion_multivano_final(
            self.puntos,ficha,1.5,
            temperaturas_C=(50.,),viento_ms=0.,
        )
        self.assertEqual(len(tabla),2)
        self.assertTrue((tabla["Continuidad residual máx. (kN)"]<1e-4).all())
        self.assertLess(
            abs(float(tabla.iloc[0]["Flecha vertical (m)"])
                -float(tabla.iloc[1]["Flecha vertical (m)"])),1e-3
        )


if __name__=="__main__":
    unittest.main()
