"""Verificador no destructivo de rutas y sintaxis."""
import ast
from pathlib import Path


def verificar():
    raiz = Path(__file__).resolve().parents[1]
    rutas = [raiz / "main.py", raiz / "app.py"]
    for carpeta in ("entradas", "calculos", "salidas", "ayuda"):
        assert (raiz / carpeta / "__init__.py").is_file(), carpeta
        rutas.extend((raiz / carpeta).glob("*.py"))
    for ruta in rutas:
        ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
    print("OK: rutas y sintaxis. No implica validación de ingeniería.")


if __name__ == "__main__":
    verificar()
