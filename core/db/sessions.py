# core/db/sessions.py
#
# DEPRECADO — Este archivo será eliminado en la próxima limpieza.
# Todos los imports deben migrar a:
#
#   from core.db.db import SessionLocal, engine
#
# Este redirector existe solo para no romper módulos durante la transición.

import warnings

warnings.warn(
    "core.db.sessions está deprecado. Usa 'from core.db.db import SessionLocal, engine' en su lugar.",
    DeprecationWarning,
    stacklevel=2,
)

from core.db.db import SessionLocal, engine  # noqa: F401, E402
