"""Topología de secciones de tendido y conexiones mecánicas explícitas."""
import unittest

from calculos.modelo_red import RedMecanica


def ejemplo():
    nodos=[
        dict(nombre=n,base_m=xyz,modelo_apoyo="PC-40")
        for n,xyz in [
            ("P1",(0,0,0)),("P2",(40,0,2)),("P3",(80,30,5)),
        ]
    ]
    vanos=[]
    for n,a,b,ca,cb in [
        ("V1","P1","P2","ANCLAJE","SUSPENSION"),
        ("V2","P2","P3","SUSPENSION","ANCLAJE"),
    ]:
        vanos.append(dict(
            nombre=n,origen=a,destino=b,circuito="C1",
            conductor="ACSR 2/0",seccion_tendido="S1",
            amarre_origen_m=(0,0,9.5),amarre_destino_m=(0,0,9.5),
            conexion_origen=ca,conexion_destino=cb,
        ))
    return nodos,vanos


class TopologiaTest(unittest.TestCase):
    def test_seccion_con_suspension_y_desnivel(self):
        nodos,vanos=ejemplo()
        red=RedMecanica.desde_registros(nodos,vanos)
        self.assertEqual(len(red.secciones()),1)
        self.assertEqual(red.secciones()[0]["Vanos"],2)
        self.assertEqual(len(red.componentes_conexas()),1)
        self.assertEqual(len(red.apoyos_conectados()["P2"]),2)

    def test_no_inferir_suspension_si_no_declara(self):
        nodos,vanos=ejemplo()
        vanos[1]["conexion_origen"]="ANCLAJE"
        with self.assertRaisesRegex(ValueError,"suspensión"):
            RedMecanica.desde_registros(nodos,vanos)

    def test_suspension_suelta_no_valida(self):
        nodos,vanos=ejemplo()
        vanos.pop()
        with self.assertRaises(ValueError):
            RedMecanica.desde_registros(nodos,vanos)

    def test_conexiones_con_diferente_conductor(self):
        nodos,vanos=ejemplo()
        vanos[1]["conductor"]="ACSR 4/0"
        with self.assertRaisesRegex(ValueError,"discontinuo"):
            RedMecanica.desde_registros(nodos,vanos)

    def test_no_admitir_ids_duplicados(self):
        nodos,vanos=ejemplo()
        vanos.append(vanos[0].copy())
        with self.assertRaisesRegex(ValueError,"duplicados"):
            RedMecanica.desde_registros(nodos,vanos)

    def test_anclajes_sin_suspension_son_secciones_separadas(self):
        nodos,vanos=ejemplo()
        vanos[0]["conexion_destino"]="ANCLAJE"
        vanos[1]["conexion_origen"]="ANCLAJE"
        vanos[1]["seccion_tendido"]="S2"
        red=RedMecanica.desde_registros(nodos,vanos)
        self.assertEqual(len(red.secciones()),2)


if __name__=="__main__":
    unittest.main()
