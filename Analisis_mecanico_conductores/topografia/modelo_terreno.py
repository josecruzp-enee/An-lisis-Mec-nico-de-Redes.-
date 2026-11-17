"""Topografía opcional: GeoTIFF local o mosaicos Terrarium públicos.

No se asume que un DSM/DEM tenga precisión de levantamiento. Toda
elevación se etiqueta como preliminar; libramiento muestreado, no certificado.
La fuente topográfica es independiente del motor termoelástico.
"""
from __future__ import annotations

from io import BytesIO
from math import asinh, cos, floor, log, pi, radians, tan
import numpy as np

from pyproj import Transformer


class ElevacionesTerrarium:
    """Consulta DEM en mosaicos Mapzen/AWS. Requiere Internet durante la corrida.

    Fuente: AWS Open Data, elevation-tiles-prod/terrarium; datos heterogéneos
    sujetos a sus licencias y resolución nativa. No equivale a Google Earth.
    """

    def __init__(self, *, zoom=13, timeout=12):
        if not (8 <= int(zoom) <= 14):
            raise ValueError("Nivel de mosaico no permitido")
        self.zoom = int(zoom)
        self.timeout = timeout
        self._cache = {}
        self.fuente = f"Mapzen Terrain Tiles / AWS Open Data (Terrarium z={self.zoom})"
        self.resolucion_aproximada_m = (
            156543.03392 * cos(radians(14.0)) / (2**self.zoom)
        )

    def elevacion(self, longitud, latitud):
        import requests
        from PIL import Image
        lon,lat=float(longitud),float(latitud)
        if not (-180 <= lon <= 180 and -85.05 < lat < 85.05):
            raise ValueError("Coordenadas fuera del rango Terrarium")
        n=2**self.zoom
        xf=(lon+180)/360*n
        yf=(1-asinh(tan(radians(lat)))/pi)/2*n
        tx,ty=floor(xf),floor(yf)
        clave=(tx,ty)
        if clave not in self._cache:
            url=(f"https://s3.amazonaws.com/elevation-tiles-prod/"
                 f"terrarium/{self.zoom}/{tx}/{ty}.png")
            try:
                respuesta=requests.get(url, timeout=self.timeout)
                respuesta.raise_for_status()
                imagen=np.asarray(Image.open(BytesIO(respuesta.content)).convert("RGB"))
                if imagen.shape != (256,256,3):
                    raise ValueError("Mosaico con dimensiones inesperadas")
            except Exception as exc:
                raise ValueError(
                    "No fue posible obtener el mosaico de elevaciones de AWS; "
                    "subí un GeoTIFF local para continuar"
                ) from exc
            self._cache[clave]=imagen
        a=self._cache[clave]
        ix=min(255,max(0,int((xf-tx)*256)))
        iy=min(255,max(0,int((yf-ty)*256)))
        r,g,b=[int(v) for v in a[iy,ix,:3]]
        return float((r*256+g+b/256)-32768)

    def cerrar(self):
        self._cache.clear()


class ElevacionesGeoTIFF:
    """Modelo DEM subido por el usuario, CRS leído del propio raster."""

    def __init__(self, datos):
        from rasterio.io import MemoryFile
        self._archivo=MemoryFile(datos)
        self._raster=self._archivo.open()
        if self._raster.crs is None:
            self.cerrar()
            raise ValueError("GeoTIFF sin CRS; no se pueden ubicar las alturas")
        if self._raster.count<1:
            self.cerrar()
            raise ValueError("GeoTIFF sin banda de elevación")
        self._transform=Transformer.from_crs("EPSG:4326",self._raster.crs,
                                             always_xy=True)
        self.fuente=f"DEM GeoTIFF aportado (CRS: {self._raster.crs})"
        self.resolucion_aproximada_m=None

    def elevacion(self,longitud,latitud):
        x,y=self._transform.transform(float(longitud),float(latitud))
        bounds=self._raster.bounds
        if not (bounds.left<=x<=bounds.right and bounds.bottom<=y<=bounds.top):
            raise ValueError("La trayectoria queda fuera del GeoTIFF")
        z=next(self._raster.sample([(x,y)],masked=True),None)
        if z is None or np.ma.is_masked(z[0]):
            raise ValueError("DEM sin datos válidos en el punto")
        valor=float(z[0])
        if not np.isfinite(valor) or (
            self._raster.nodata is not None and valor==self._raster.nodata
        ):
            raise ValueError("Elevación ausente / nodata en el DEM")
        return valor

    def cerrar(self):
        self._raster.close()
        self._archivo.close()


def extraer_terreno_apoyos(puntos, elevaciones, *, epsg_xy=32616):
    """Copia de puntos con altitudes muestreadas del DEM, sin alterar el origen.

    La altura de amarre es una entrada independiente, no la elevación del DEM.
    """
    if "Altura_Amarre_m" not in puntos or puntos["Altura_Amarre_m"].isna().any():
        raise ValueError("Se necesita altura de amarre para cada apoyo")
    p=puntos.copy(deep=True)
    convertir=Transformer.from_crs(int(epsg_xy),4326,always_xy=True)
    cotas=[]
    for x,y in p[["X","Y"]].itertuples(index=False,name=None):
        lon,lat=convertir.transform(float(x),float(y))
        cotas.append(float(elevaciones.elevacion(lon,lat)))
    p["Altitud"]=cotas
    return p


def calcular_libramientos_muestreados(
    tabla, puntos, propiedades_por_estado, elevaciones,
    *, epsg_xy=32616, paso_m=2., clima=None,
):
    """Distancia vertical conductor-superficie en trayectoria 3D desplazada.

    NO asegura mínimo continuo entre píxeles DEM; conserva clasificación
    preliminar. Para viento se evalúa terreno en XY desplazado de la curva.
    """
    from Analisis_mecanico_conductores.tension_tendido.calcular_tension_y_flechas_de_seccion import _geometria
    from Analisis_mecanico_conductores.catenaria.resolver_catenaria_exacta import resolver_catenaria
    from salidas.PDF.graficos_catenarias_cfe import _carga
    import pandas as pd
    if paso_m<=0 or not np.isfinite(paso_m):
        raise ValueError("Paso de perfil inválido")
    xyz,_=_geometria(puntos)
    nombres=[f"{a} → {b}" for a,b in zip(
        puntos["Punto"].astype(str).iloc[:-1],
        puntos["Punto"].astype(str).iloc[1:]
    )]
    transformar=Transformer.from_crs(int(epsg_xy),4326,always_xy=True)
    salida=[]
    perfiles=[]
    for i,nombre in enumerate(nombres):
        sub=tabla[tabla["Vano"]==nombre]
        if sub.empty:
            raise ValueError(f"Vano sin resultados: {nombre}")
        for _,fila in sub.iterrows():
            prop=propiedades_por_estado[fila["Condición"]]
            q=_carga(xyz,i,fila,prop,clima or {})
            cable=resolver_catenaria(xyz[i],xyz[i+1],q,float(fila["H (kN)"]))
            muestras=max(3,int(np.ceil(float(cable.luz)/paso_m))+1)
            xx=np.linspace(0.,float(cable.luz),muestras)
            posiciones=cable.puntos(xx)
            elev=[]
            for p in posiciones:
                lon,lat=transformar.transform(float(p[0]),float(p[1]))
                elev.append(elevaciones.elevacion(lon,lat))
            elev=np.asarray(elev,dtype=float)
            despejes=posiciones[:,2]-elev
            k=int(np.argmin(despejes))
            d_xy=np.linalg.norm(posiciones[:,:2]-xyz[i,:2],axis=1)
            salida.append({
                "Condición":fila["Condición"],"Hipótesis":fila["Hipótesis"],
                "Temperatura (°C)":float(fila["Temperatura (°C)"]),
                "Vano":nombre,"Distancia crítica desde apoyo (m)":float(d_xy[k]),
                "Libramiento mínimo muestreado (m)":float(despejes[k]),
                "Cota terreno crítica (m)":float(elev[k]),
                "Cota conductor crítica (m)":float(posiciones[k,2]),
                "Paso solicitado (m)":float(paso_m),
                "Fuente topográfica":elevaciones.fuente,
                "Clasificación":"PRELIMINAR - DEM",
            })
            perfiles.extend({
                "Vano":nombre,"Condición":fila["Condición"],
                "Hipótesis":fila["Hipótesis"],
                "Temperatura (°C)":float(fila["Temperatura (°C)"]),
                "Distancia desde apoyo (m)":float(d),
                "Elevación terreno (m)":float(z),
                "Elevación conductor (m)":float(c),
                "Libramiento vertical (m)":float(l),
            } for d,z,c,l in zip(d_xy,elev,posiciones[:,2],despejes))
    return pd.DataFrame(salida), pd.DataFrame(perfiles)


def leer_apoyos_kml(datos, *, epsg_xy=32616):
    """Importa apoyos KML en orden de la polilínea LP y transforma WGS84 a UTM.

    Altitud se deja VACÍA: los atributos KML 'absolute' de marcadores
    no garantizan una cota topográfica; 0 'relativeToGround' tampoco.
    No se inventan alturas de amarre.
    """
    import re
    from xml.etree import ElementTree as ET
    import pandas as pd
    try:
        raiz=ET.fromstring(datos)
    except ET.ParseError as exc:
        raise ValueError("KML no es XML válido") from exc
    ns={"k":"http://www.opengis.net/kml/2.2"}
    puntos=[]
    recorrido=[]
    for elemento in raiz.findall(".//k:Placemark",ns):
        nombre=(elemento.findtext("k:name",default="",namespaces=ns) or "").strip()
        pt=elemento.find(".//k:Point/k:coordinates",ns)
        linea=elemento.find(".//k:LineString/k:coordinates",ns)
        if linea is not None and linea.text and not recorrido:
            for parte in linea.text.split():
                v=parte.split(",")
                if len(v)>=2:
                    recorrido.append((float(v[0]),float(v[1])))
        if pt is not None and pt.text and re.match(r"^P[-.\s]*\d+",nombre,re.I):
            valores=pt.text.strip().split(",")
            if len(valores)<2:
                continue
            lon,lat=float(valores[0]),float(valores[1])
            if not (-180<=lon<=180 and -90<=lat<=90):
                raise ValueError("Coordenada geográfica KML inválida")
            puntos.append((nombre,lon,lat))
    if len(puntos)<2:
        raise ValueError("El KML debe contener al menos dos marcadores P-xx")
    if recorrido:
        # Proyección aproximada sobre cada segmento de la ruta, no orden alfabético.
        # Útil cuando el archivo enumera los marcadores en distinto orden.
        tf=Transformer.from_crs(4326,int(epsg_xy),always_xy=True)
        tr=np.asarray([tf.transform(*par) for par in recorrido])
        def distancia_recorrida(pt):
            xy=np.asarray(tf.transform(pt[1],pt[2]))
            mejor=(float("inf"),float("inf"))
            acum=0.
            for a,b in zip(tr[:-1],tr[1:]):
                v=b-a
                l=float(np.linalg.norm(v))
                if l==0:
                    continue
                t=float(np.clip(np.dot(xy-a,v)/(l*l),0,1))
                dis=float(np.linalg.norm(xy-(a+t*v)))
                mejor=min(mejor,(dis,acum+t*l))
                acum+=l
            return mejor[1]
        puntos.sort(key=distancia_recorrida)
    tf=Transformer.from_crs(4326,int(epsg_xy),always_xy=True)
    datos_tabla=[]
    for nombre,lon,lat in puntos:
        x,y=tf.transform(lon,lat)
        datos_tabla.append({
            "Punto":nombre,"X":float(x),"Y":float(y),
            "Altitud":float("nan"),"Altura_Amarre_m":float("nan"),
        })
    return pd.DataFrame(datos_tabla)
