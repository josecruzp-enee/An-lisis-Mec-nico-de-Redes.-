"""Ejemplo reproducible con geometría de tres apoyos y propiedades SINTÉTICAS.

Ejecutar desde la raíz: python -m ayuda.ejemplo_barrido_3d
No utilizar los parámetros termomecánicos ficticios en construcción.
"""
from calculos.barrido_3d import ejecutar_barrido_3d


def ejemplo():
    nodos = {
        "P1": ((371096.204, 1698476.520, 0.0), (0.0, 0.0, 9.5)),
        "P2": ((371051.759, 1698486.420, 2.0), (0.0, 0.0, 9.2)),
        "P3": ((371041.859, 1698441.980, 5.0), (0.0, 0.0, 9.0)),
    }
    vanos = []
    for inicio, fin in (("P1", "P2"), ("P2", "P3")):
        base_a, amarre_a = nodos[inicio]
        base_b, amarre_b = nodos[fin]
        vanos.append({
            "nombre": inicio + "-" + fin,
            "inicio": inicio, "fin": fin,
            "base_inicio_m": base_a, "base_fin_m": base_b,
            "amarre_inicio_m": amarre_a, "amarre_fin_m": amarre_b,
        })
    return ejecutar_barrido_3d(
        vanos,
        peso_kN_m=0.272*9.80665/1000,  # 2/0 ACSR, solo masa del catálogo
        diametro_m=0.01134,
        EA_kN=16000,                   # ¡SINTÉTICO, NO FICHA 2/0!
        alpha_por_C=1.8e-5,            # ¡SINTÉTICO, NO FICHA 2/0!
        temperatura_tendido_C=20,
        temperaturas_C=[20, 40],
        tensiones_iniciales_kN=[4, 6, 8],
        viento_min_ms=0,
        viento_max_ms=10,
        incremento_viento_ms=1,
        direcciones_viento_deg=[0, 180],
        cantidad_conductores=3,
        fuente_conductor="ENSAYO SINTÉTICO: EA/alpha NO verificados para 2/0 ACSR",
    )


if __name__ == "__main__":
    resultado = ejemplo()
    print("Estados de vano:", len(resultado["vanos"]))
    print("Acciones por apoyo:", len(resultado["nodos"]))
    print("Mayor residual de equilibrio (kN):",
          resultado["vanos"]["Residual equilibrio (kN)"].max())
    print(resultado["nodos"].head(6).to_string(index=False))
