"""Validación de los puntos importados sin modificar el motor mecánico."""
import numpy as np


def validar_puntos_excel(df) -> None:
    """Identificadores únicos, coordenadas finitas y vanos no degenerados."""
    if len(df) < 2:
        raise ValueError("Se requieren al menos dos puntos")
    nombres = df["Punto"].astype(str).str.strip()
    if nombres.isin(("", "nan", "None")).any() or nombres.duplicated().any():
        raise ValueError("Los puntos deben tener identificadores únicos y no vacíos")
    xy = df[["X", "Y"]].to_numpy(dtype=float)
    if not np.isfinite(xy).all():
        raise ValueError("Las coordenadas X/Y deben ser finitas")
    if (np.linalg.norm(np.diff(xy, axis=0), axis=1) <= 0).any():
        raise ValueError("Hay puntos consecutivos coincidentes; vano de longitud cero")
