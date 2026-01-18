# tools/mapa_proyecto.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import ast
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional


EXCLUDE_DIRS = {
    ".git", ".venv", "venv", "__pycache__", ".mypy_cache", ".pytest_cache",
    ".streamlit", "build", "dist", "node_modules", ".idea", ".vscode"
}

INCLUDE_EXT = {".py"}


@dataclass
class PyInfo:
    path: str
    module: str
    imports: List[str] = field(default_factory=list)
    from_imports: List[Tuple[str, List[str]]] = field(default_factory=list)  # (module, names)
    functions: List[str] = field(default_factory=list)  # "def name(args)"
    classes: List[str] = field(default_factory=list)    # "class Name(bases)"
    errors: List[str] = field(default_factory=list)


def _to_module(root: str, file_path: str) -> str:
    rel = os.path.relpath(file_path, root).replace(os.sep, "/")
    if rel.endswith(".py"):
        rel = rel[:-3]
    if rel.endswith("/__init__"):
        rel = rel[:-9]
    return rel.replace("/", ".")


def _sig_from_func(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args = []
    for a in node.args.posonlyargs:
        args.append(a.arg)
    if node.args.posonlyargs:
        args.append("/")  # marcador pos-only
    for a in node.args.args:
        args.append(a.arg)
    if node.args.vararg:
        args.append("*" + node.args.vararg.arg)
    elif node.args.kwonlyargs:
        args.append("*")
    for a in node.args.kwonlyargs:
        args.append(a.arg)
    if node.args.kwarg:
        args.append("**" + node.args.kwarg.arg)
    return f"def {node.name}({', '.join(args)})"


def _sig_from_class(node: ast.ClassDef) -> str:
    bases = []
    for b in node.bases:
        try:
            bases.append(ast.unparse(b))
        except Exception:
            bases.append("<base>")
    base_txt = f"({', '.join(bases)})" if bases else ""
    return f"class {node.name}{base_txt}"


def _parse_py(root: str, path: str) -> PyInfo:
    info = PyInfo(path=path, module=_to_module(root, path))
    try:
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()
        tree = ast.parse(src, filename=path)
    except Exception as e:
        info.errors.append(f"ParseError: {e}")
        return info

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                info.imports.append(n.name)
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            names = [n.name for n in node.names]
            info.from_imports.append((mod, names))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # solo top-level: evita funciones internas revisando parent con un truco simple:
            # (ast no trae parent, así que filtramos por col_offset == 0)
            if getattr(node, "col_offset", 1) == 0:
                info.functions.append(_sig_from_func(node))
        elif isinstance(node, ast.ClassDef):
            if getattr(node, "col_offset", 1) == 0:
                info.classes.append(_sig_from_class(node))

    # normaliza y quita duplicados preservando orden
    def uniq(xs):
    """
    Devuelve lista sin duplicados conservando orden.
    Soporta elementos no-hasheables (listas/dicts) convirtiéndolos a una clave estable.
    """
    seen = set()
    out = []

    def key(v):
        if isinstance(v, (list, tuple)):
            return tuple(key(i) for i in v)
        if isinstance(v, dict):
            return tuple(sorted((k, key(val)) for k, val in v.items()))
        return v

    for x in xs:
        k = key(x)
        if k not in seen:
            seen.add(k)
            out.append(x)
    return out



def _walk_py_files(root: str) -> List[str]:
    py_files = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for fn in files:
            ext = os.path.splitext(fn)[1].lower()
            if ext in INCLUDE_EXT:
                py_files.append(os.path.join(base, fn))
    py_files.sort()
    return py_files


def _tree_view(root: str, files: List[str]) -> str:
    # árbol simple basado en paths relativos
    rels = [os.path.relpath(p, root).replace(os.sep, "/") for p in files]
    rels.sort()
    out = []
    last_parts: List[str] = []
    for r in rels:
        parts = r.split("/")
        # encuentra prefijo común
        common = 0
        for a, b in zip(last_parts, parts):
            if a == b:
                common += 1
            else:
                break
        # imprime desde common
        for i in range(common, len(parts)):
            indent = "  " * i
            out.append(f"{indent}- {parts[i]}")
        last_parts = parts
    return "\n".join(out)


def generar_mapa(root: str, out_md: str = "MAPA_DEL_PROYECTO.md") -> str:
    files = _walk_py_files(root)
    infos = [_parse_py(root, p) for p in files]

    # índice por módulo
    by_mod: Dict[str, PyInfo] = {i.module: i for i in infos}

    # dependencias: mod -> lista de imports (solo los que parecen locales)
    deps: Dict[str, List[str]] = {}
    for i in infos:
        local = []
        for imp in i.imports:
            if imp in by_mod or any((imp + ".") == m[: len(imp) + 1] for m in by_mod):
                local.append(imp)
        for mod, _names in i.from_imports:
            if not mod:
                continue
            if mod in by_mod or any((mod + ".") == m[: len(mod) + 1] for m in by_mod):
                local.append(mod)
        # uniq
        seen = set()
        local2 = []
        for x in local:
            if x not in seen:
                seen.add(x)
                local2.append(x)
        deps[i.module] = local2

    lines: List[str] = []
    lines.append("# MAPA DEL PROYECTO\n")
    lines.append(f"Raíz analizada: `{os.path.abspath(root)}`\n")
    lines.append("## Árbol de archivos (.py)\n")
    lines.append("```")
    lines.append(_tree_view(root, files))
    lines.append("```\n")

    lines.append("## Resumen por archivo\n")
    for i in infos:
        rel = os.path.relpath(i.path, root).replace(os.sep, "/")
        lines.append(f"### `{rel}`  ({i.module})\n")

        if i.errors:
            lines.append("**Errores:**")
            for e in i.errors:
                lines.append(f"- {e}")
            lines.append("")
            continue

        if i.imports or i.from_imports:
            lines.append("**Imports:**")
            for imp in i.imports:
                lines.append(f"- import {imp}")
            for mod, names in i.from_imports:
                names_txt = ", ".join(names)
                lines.append(f"- from {mod} import {names_txt}")
            lines.append("")

        if i.classes:
            lines.append("**Clases:**")
            for c in i.classes:
                lines.append(f"- `{c}`")
            lines.append("")

        if i.functions:
            lines.append("**Funciones:**")
            for f in i.functions:
                lines.append(f"- `{f}`")
            lines.append("")

        # deps locales
        d = deps.get(i.module, [])
        if d:
            lines.append("**Dependencias locales (aprox):**")
            for x in d:
                lines.append(f"- {x}")
            lines.append("")

    lines.append("## Grafo simple (módulo -> dependencias locales)\n")
    lines.append("```")
    for k in sorted(deps.keys()):
        ds = deps[k]
        if ds:
            lines.append(f"{k} -> {', '.join(ds)}")
        else:
            lines.append(f"{k} -> (sin deps locales detectadas)")
    lines.append("```")

    content = "\n".join(lines) + "\n"
    with open(os.path.join(root, out_md), "w", encoding="utf-8") as f:
        f.write(content)
    return os.path.join(root, out_md)


if __name__ == "__main__":
    # Uso:
    #   python tools/mapa_proyecto.py .
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    out = generar_mapa(root)
    print(f"OK -> {out}")
