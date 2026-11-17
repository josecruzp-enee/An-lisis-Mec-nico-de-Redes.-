"""Pruebas offline de importación KML, DEM GeoTIFF y libramientos 3D."""
from io import BytesIO
import unittest
import numpy as np
import pandas as pd

from Analisis_mecanico_conductores.topografia.modelo_terreno import (
    leer_apoyos_kml, ElevacionesGeoTIFF, extraer_terreno_apoyos,
    calcular_libramientos_muestreados,
)
from Analisis_mecanico_conductores.tension_tendido.ejecutar_corridas_cfe_documentadas import (
    seleccionar_propiedades_cfe_07_ft_01,
)
from Analisis_mecanico_conductores.tension_tendido.calcular_tablas_cfe_inicial_final import (
    PropiedadesConductorCFE, EstadoReferenciaCFE, calcular_tablas_inicial_final,
)


class FuentePlana:
    fuente="Superficie de ensayo 100 m (no DEM real)"
    def elevacion(self, lon, lat):
        return 100.


class TopografiaModulo1(unittest.TestCase):
    def test_kml_importa_orden_y_no_inventa_cotas(self):
        kml=b"""<?xml version="1.0" encoding="UTF-8"?>
        <kml xmlns="http://www.opengis.net/kml/2.2"><Document>
        <Placemark><name>P-03</name><Point><coordinates>-88.6369,14.0510,0</coordinates></Point></Placemark>
        <Placemark><name>LP</name><LineString><coordinates>-88.6383,14.0510,0 -88.6377,14.0510,0 -88.6369,14.0510,0</coordinates></LineString></Placemark>
        <Placemark><name>P-01</name><Point><coordinates>-88.6383,14.0510,275</coordinates></Point></Placemark>
        <Placemark><name>P-02</name><Point><coordinates>-88.6377,14.0510,275</coordinates></Point></Placemark>
        </Document></kml>"""
        p=leer_apoyos_kml(kml)
        self.assertEqual(list(p["Punto"]),["P-01","P-02","P-03"])
        self.assertTrue(p["Altitud"].isna().all())
        self.assertTrue(p["Altura_Amarre_m"].isna().all())

    def test_dem_local_cotas_transformadas(self):
        import rasterio
        from rasterio.io import MemoryFile
        from rasterio.transform import from_origin
        from pyproj import Transformer
        lon,lat=-88.6383,14.0510
        x,y=Transformer.from_crs(4326,32616,always_xy=True).transform(lon,lat)
        datos=np.full((1,32,32),120.,dtype="float32")
        with MemoryFile() as memoria:
            with memoria.open(driver="GTiff",height=32,width=32,count=1,
                              dtype="float32",crs="EPSG:32616",
                              transform=from_origin(x-160,y+160,10,10)) as tif:
                tif.write(datos)
            dem=ElevacionesGeoTIFF(memoria.read())
            self.assertAlmostEqual(dem.elevacion(lon,lat),120.)
            puntos=pd.DataFrame({
                "Punto":["A","B"],"X":[x,x+20],"Y":[y,y],
                "Altura_Amarre_m":[9.5,9.5],"Altitud":[100.,100.],
            })
            ajustados=extraer_terreno_apoyos(puntos,dem)
            self.assertAlmostEqual(float(ajustados["Altitud"].iloc[0]),120.)
            self.assertAlmostEqual(float(puntos["Altitud"].iloc[0]),100.)
            dem.cerrar()

    def test_libramientos_geometria_exacta_con_viento(self):
        ini,fin=seleccionar_propiedades_cfe_07_ft_01("RAVEN")
        props=PropiedadesConductorCFE(
            peso_kN_m=ini["peso_kN_m"],diametro_m=ini["diametro_m"],
            EA_inicial_kN=ini["EA_kN"],EA_final_kN=fin["EA_kN"],
            alpha_inicial_por_C=ini["alpha_por_C"],
            alpha_final_por_C=fin["alpha_por_C"],
            ruptura_kN=ini["ruptura_kN"],fuente="CFE",
        )
        x,y=323090.,1553974.
        puntos=pd.DataFrame({
            "Punto":["A","B"],"X":[x,x+50],"Y":[y,y],
            "Altitud":[100.,100.],"Altura_Amarre_m":[9.5,9.5],
        })
        tabla=calcular_tablas_inicial_final(
            puntos,props,EstadoReferenciaCFE(760.,"CFE"),
            EstadoReferenciaCFE(660.,"CFE"),[20.,50.],
            estados_climaticos=[("CFE viento máximo",0.,120.,0.)],Cd=1.,
        )
        libr, perfil=calcular_libramientos_muestreados(
            tabla,puntos,{"Inicial":ini,"Final":fin},FuentePlana(),
            paso_m=2.,epsg_xy=32616,clima={"Cd":1.,"rho_kg_m3":1.225},
        )
        self.assertEqual(len(libr),6)
        self.assertGreater(len(perfil),100)
        self.assertTrue((libr["Libramiento mínimo muestreado (m)"]>0).all())
        self.assertTrue((libr["Libramiento mínimo muestreado (m)"]<9.5).all())
        self.assertTrue((libr["Clasificación"]=="PRELIMINAR - DEM").all())


if __name__=="__main__":
    unittest.main()
