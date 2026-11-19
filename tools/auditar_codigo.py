"""Auditoría estática reproducible de TODOS los archivos Python del repositorio.

No elimina automáticamente archivos: distingue código potencialmente muerto,
duplicados exactos y funciones equivalentes. Ejecución: python tools/auditar_codigo.py
"""
from __future__ import annotations

import ast
from collections import defaultdict
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORADOS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache"}
INICIOS = {"main", "app", "mapa_proyecto"}
CARPETAS_FUNCIONALES = {
    "Analisis_mecanico_conductores", "Analisis_mecanico_estructuras",
    "comun", "calculos", "entradas"
}


def rutas():
    return sorted(p for p in ROOT.rglob("*.py")
                  if not any(x in IGNORADOS for x in p.relative_to(ROOT).parts))


def modulo(p):
    trozos = list(p.relative_to(ROOT).with_suffix("").parts)
    if trozos[-1] == "__init__":
        trozos.pop()
    return ".".join(trozos)


def resolver(base, nivel, actual, es_paquete):
    if not nivel:
        return base or ""
    p = actual.split(".") if actual else []
    if not es_paquete:
        p = p[:-1]
    recorte = nivel - 1
    p = p[:max(0, len(p) - recorte)]
    if base:
        p.append(base)
    return ".".join(x for x in p if x)


def auditoria():
    archivos = rutas()
    contenidos = {p: p.read_text(encoding="utf-8-sig") for p in archivos}
    por_modulo = {modulo(p): p for p in archivos}
    refs = defaultdict(set)
    problemas = []
    imports_inexistentes = []
    defs = defaultdict(list)
    digest = defaultdict(list)
    clases = defaultdict(int)
    candidatos = []
    enlaces = []
    shims = []
    funciones = 0

    for p, src in contenidos.items():
        rel = p.relative_to(ROOT).as_posix()
        m = modulo(p)
        clases[rel.split("/")[0]] += 1
        digest[hashlib.sha256(src.encode()).hexdigest()].append(rel)
        try:
            arbol = ast.parse(src, filename=rel)
        except SyntaxError as e:
            problemas.append(f"{rel}:{e.lineno}: {e.msg}")
            continue
        es_paquete = p.name == "__init__.py"
        para = set()
        for nodo in ast.walk(arbol):
            posibles = []
            if isinstance(nodo, ast.Import):
                posibles.extend(a.name for a in nodo.names)
            elif isinstance(nodo, ast.ImportFrom):
                ruta = resolver(nodo.module, nodo.level, m, es_paquete)
                if (ruta.split(".")[0] in CARPETAS_FUNCIONALES
                        and ruta not in por_modulo):
                    imports_inexistentes.append(f"{rel}:{nodo.lineno} -> {ruta}")
                posibles.append(ruta)
                posibles.extend(ruta + "." + a.name for a in nodo.names if a.name != "*")
            elif isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name) and nodo.func.id in ("__import__", "import_module"):
                if nodo.args and isinstance(nodo.args[0], ast.Constant) and isinstance(nodo.args[0].value, str):
                    posibles.append(nodo.args[0].value)
            for imp in posibles:
                # from paquete import simbolo puede designar un submódulo.
                opciones = imp.split(".")
                for i in range(len(opciones), 0, -1):
                    target = ".".join(opciones[:i])
                    if target in por_modulo and target != m:
                        para.add(target)
                        break
            if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)) and nodo.lineno > 0:
                funciones += 1
                if len(nodo.body) >= 3 or (nodo.end_lineno or 0) - nodo.lineno >= 10:
                    copia = ast.FunctionDef(
                        name="_", args=nodo.args, body=nodo.body,
                        decorator_list=[], returns=None, type_comment=None,
                    )
                    # Retirar docstring y no usar nombre para hallar copia funcional.
                    if copia.body and isinstance(copia.body[0], ast.Expr) and isinstance(copia.body[0].value, ast.Constant) and isinstance(copia.body[0].value.value, str):
                        copia.body = copia.body[1:]
                    clave = hashlib.sha256(ast.dump(copia, include_attributes=False).encode()).hexdigest()
                    defs[clave].append((rel, nodo.name, nodo.end_lineno - nodo.lineno + 1))
        enlaces.extend((rel, t) for t in sorted(para))
        for t in para:
            refs[t].add(rel)
        if ("Ruta histórica" in src or "Compatibilidad de importación" in src
                or "Ruta de compatibilidad" in src or "Importación compatible" in src):
            shims.append(rel)

    for p in archivos:
        rel = p.relative_to(ROOT).as_posix()
        m = modulo(p)
        if (m not in refs and p.name != "__init__.py"
                and rel.split("/")[0] in CARPETAS_FUNCIONALES):
            # La ausencia de imports estáticos es una pista, NO una prueba.
            candidatos.append(rel)

    # Recorrido de dependencias en cadena desde entradas reales y tests.
    # Permite detectar módulos que solo se importan entre sí, sin consumidores.
    adyacencia = defaultdict(set)
    for fuente, destino in enlaces:
        adyacencia[fuente].add(destino)
    raices = {
        p.relative_to(ROOT).as_posix() for p in archivos
        if p.relative_to(ROOT).as_posix() in (
            "main.py", "app.py", "mapa_proyecto.py"
        ) or p.relative_to(ROOT).as_posix().startswith("tests/")
        or "/pruebas/" in p.relative_to(ROOT).as_posix()
        or p.relative_to(ROOT).as_posix().startswith("ayuda/")
    }
    visitados = set(raices)
    pendientes = list(raices)
    while pendientes:
        actual = pendientes.pop()
        for importado in adyacencia.get(actual, ()):
            ruta = por_modulo.get(importado)
            if ruta is None:
                continue
            nombre = ruta.relative_to(ROOT).as_posix()
            if nombre not in visitados:
                visitados.add(nombre)
                pendientes.append(nombre)
    aislados = [
        p.relative_to(ROOT).as_posix() for p in archivos
        if p.relative_to(ROOT).as_posix() not in visitados
        and p.relative_to(ROOT).parts[0] in CARPETAS_FUNCIONALES
        and p.name != "__init__.py"
    ]
    def alcanzables(raices):
        alcanzados = set(raices)
        cola = list(raices)
        while cola:
            for importado in adyacencia.get(cola.pop(), ()):
                destino = por_modulo.get(importado)
                if destino is not None:
                    nombre = destino.relative_to(ROOT).as_posix()
                    if nombre not in alcanzados:
                        alcanzados.add(nombre)
                        cola.append(nombre)
        return alcanzados

    # Diferenciar el motor verdaderamente requerido por la aplicación
    # de módulos a los que solo acceden pruebas automáticas.
    ejecucion = alcanzables({"main.py", "app.py"})
    pruebas = alcanzables({
        p.relative_to(ROOT).as_posix() for p in archivos
        if p.relative_to(ROOT).as_posix().startswith("tests/")
        or "/pruebas/" in p.relative_to(ROOT).as_posix()
    })
    modulos_reales = {
        p.relative_to(ROOT).as_posix() for p in archivos
        if p.relative_to(ROOT).parts[0] in CARPETAS_FUNCIONALES
        and p.name != "__init__.py"
    }
    solo_pruebas = sorted((pruebas - ejecucion) & modulos_reales)
    sin_ejecucion = sorted(modulos_reales - ejecucion)
    exactos = [v for v in digest.values() if len(v) > 1]
    similitud = [v for v in defs.values() if len({x[0] for x in v}) > 1
                 and max(x[2] for x in v) >= 10]
    similitud.sort(key=lambda v: (-max(x[2] for x in v), -len(v)))
    print("AUDITORÍA ESTÁTICA INTEGRAL")
    print("Archivos Python examinados:", len(archivos))
    print("Funciones examinadas:", funciones)
    print("Importaciones internas dirigidas:", len(enlaces))
    print("Archivos por paquete:", dict(sorted(clases.items())))
    print("Errores de sintaxis:", problemas or "Ninguno")
    print("Imports internos inexistentes:", imports_inexistentes or "Ninguno")
    print("Copias byte a byte:", exactos or "Ninguna")
    print("Rutas de compatibilidad:", len(shims))
    print("Módulos funcionales sin importación estática entrante:", len(candidatos))
    for p in candidatos:
        print("SIN_REF_ESTATICA", p)
    print("Módulos fuera de toda ruta desde UI y pruebas:", len(aislados))
    for p in aislados:
        print("AISLADO", p)
    print("Módulos productivos alcanzables desde Streamlit:", len(ejecucion & modulos_reales))
    print("Módulos productivos utilizados solo por pruebas:", len(solo_pruebas))
    for p in solo_pruebas:
        print("SOLO_PRUEBAS", p)
    print("Módulos no alcanzables desde Streamlit:", len(sin_ejecucion))
    for p in sin_ejecucion:
        print("FUERA_APP", p)
    print("Grupos de funciones equivalentes en módulos diferentes:", len(similitud))
    for grupo in similitud[:100]:
        print("FUNCION_DUPLICADA", grupo)
    return not problemas and not imports_inexistentes


if __name__ == "__main__":
    raise SystemExit(0 if auditoria() else 1)
