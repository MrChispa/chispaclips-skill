#!/usr/bin/env python3
"""Shim retrocompatible: `python chispaclips.py <subcomando>`.

Permite a los usuarios que aún invocan la skill con la sintaxis del
repositorio original (un solo archivo) seguir funcionando sin cambios.
Internamente delega al paquete `chispaclips`.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Permite importar el paquete hermano cuando se ejecuta este archivo directamente.
_AQUI = Path(__file__).resolve().parent
if str(_AQUI) not in sys.path:
    sys.path.insert(0, str(_AQUI))

from chispaclips.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
