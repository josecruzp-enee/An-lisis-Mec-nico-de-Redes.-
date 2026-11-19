"""Regresión del único motor operativo de conductores: sin cambiar solvers."""
import unittest
from unittest.mock import patch
import pandas as pd

from Analisis_mecanico_conductores.motor_conductores import (
    ejecutar_motor_conductores, _diagnosticar,
)


def _salidas():
    resumen = pd.DataFrame({
        "Condición": ["Inicial", "Final"],
        "Igualdad extrema publicada verificada": [False, False],
        "Diferencia real de acoplamiento H4 (kN)": [0.01, 0.01],
        "Deformación aparente inicial→final máxima |ΔL0/L0|": [0.0003, 0.0003],
    })
    tabla = pd.DataFrame({
        "Condición": ["Inicial", "Final"],
        "Residual (m)": [1e-9, -2e-9],
        "T máx. (kN)": [2., 1.9],
        "H (kN)": [1.5, 1.4],
    })
    return resumen, tabla


class MotorUnicoConductoresTests(unittest.TestCase):
    def test_exige_presion_cfe(self):
        with self.assertRaisesRegex(ValueError, "presiones tabuladas"):
            ejecutar_motor_conductores(None, None, None,
                viento_max_kmh=120, viento_reducido_kmh=109,
                hielo_mm=0, temperaturas_C=[50],
                modelo_presion_cfe=False)

    def test_unica_llamada_motor_cfe_sin_alterar_tabla(self):
        resumen, tabla = _salidas()
        with patch(
            "Analisis_mecanico_conductores.motor_conductores.ejecutar_corridas_cfe_por_vano",
            return_value=(resumen, tabla),
        ) as solver:
            out_resumen, out_tabla = ejecutar_motor_conductores(
                object(), {"fuente": "x"}, {"fuente": "y"},
                viento_max_kmh=120, viento_reducido_kmh=109,
                hielo_mm=6, temperaturas_C=[0, 16, 50],
            )
        self.assertEqual(solver.call_count, 1)
        self.assertTrue(solver.call_args.kwargs["modelo_presion_cfe"])
        self.assertTrue(solver.call_args.kwargs["longitud_comun_sin_creep"])
        pd.testing.assert_frame_equal(out_tabla, tabla)
        self.assertFalse(out_resumen["Evolución material validada"].any())
        self.assertEqual(len(out_resumen), 2)

    def test_no_acepta_inconsistencia_de_longitud(self):
        resumen, tabla = _salidas()
        tabla.loc[0, "Residual (m)"] = 0.001
        with self.assertRaisesRegex(ValueError, "fuera de tolerancia"):
            _diagnosticar(resumen, tabla, presion_cfe=True)

    def test_no_confunde_igualdad_extrema_con_creep(self):
        resumen, tabla = _salidas()
        resumen["Igualdad extrema publicada verificada"] = True
        diagnostico = _diagnosticar(resumen, tabla, presion_cfe=True)
        self.assertTrue(diagnostico.igualdad_extrema_reportada)
        self.assertFalse(diagnostico.creep_constitutivo_validado)


class CompatibilidadFisicaSinCreep(unittest.TestCase):
    def test_longitud_natural_inicial_final_identica_por_vano(self):
        from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import (
            seleccionar_propiedades_cfe_07_ft_01,
        )
        inicial, final = seleccionar_propiedades_cfe_07_ft_01("RAVEN")
        puntos = pd.DataFrame({
            "Punto": ["P1", "P2"],
            "X": [0., 50.], "Y": [0., 0.],
            "Altitud": [100., 100.], "Altura_Amarre_m": [9.5, 9.5],
        })
        resumen, tabla = ejecutar_motor_conductores(
            puntos, inicial, final,
            viento_max_kmh=120., viento_reducido_kmh=109.,
            hielo_mm=0., temperaturas_C=[0., 16., 50.],
        )
        naturales=tabla.groupby("Condición")["Longitud natural fijada (m)"].first()
        self.assertAlmostEqual(float(naturales["Inicial"]),
                               float(naturales["Final"]), places=10)
        self.assertEqual(float(resumen["Creep adicional"].iloc[0]), 0.)
        self.assertTrue((tabla["Residual (m)"].abs() < 1e-7).all())
        self.assertGreater(float(tabla["T máx. (kN)"].min()), 0.)
