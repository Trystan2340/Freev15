#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Valide les fichiers de donnees Freev sans modifier leur contenu."""

from pathlib import Path
import sys


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_FILES = ["freev_data.txt", "freev_eval.txt"]


def normalize_question(text: str) -> str:
    return " ".join(text.strip().lower().split())


def validate(path: Path) -> dict:
    raw = path.read_bytes()
    errors = []
    if b"\x00" in raw:
        errors.append("contient au moins un octet NUL")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        return {
            "file": str(path),
            "ok": False,
            "pairs": 0,
            "errors": [f"UTF-8 invalide: {exc}"],
            "duplicates": 0,
        }

    pairs = 0
    duplicates = 0
    seen = set()
    malformed = 0
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=>" not in stripped:
            malformed += 1
            errors.append(f"ligne {lineno}: separateur => manquant")
            continue
        q, r = stripped.split("=>", 1)
        if not q.strip() or not r.strip():
            malformed += 1
            errors.append(f"ligne {lineno}: question ou reponse vide")
            continue
        key = normalize_question(q)
        if key in seen:
            duplicates += 1
        seen.add(key)
        pairs += 1

    return {
        "file": str(path),
        "ok": not errors,
        "pairs": pairs,
        "errors": errors,
        "duplicates": duplicates,
        "malformed": malformed,
    }


def main(argv: list[str]) -> int:
    targets = [Path(arg) for arg in argv[1:]] if len(argv) > 1 else [BASE_DIR / name for name in DEFAULT_FILES]
    exit_code = 0
    for target in targets:
        path = target if target.is_absolute() else BASE_DIR / target
        if not path.exists():
            print(f"{path}: introuvable")
            exit_code = 1
            continue
        result = validate(path)
        status = "OK" if result["ok"] else "ERREUR"
        print(f"{status} {path.name}: {result['pairs']} paires, {result['duplicates']} doublons exacts")
        for error in result["errors"][:10]:
            print(f"  - {error}")
        if len(result["errors"]) > 10:
            print(f"  - ... {len(result['errors']) - 10} erreurs supplementaires")
        if not result["ok"]:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
