# core/exceptions.py


class LOBOError(Exception):
    """
    Excepción base de LOBO.
    Todas las excepciones del sistema heredan de esta clase.
    """

    def __init__(self, message: str, module: str = "core", details: str = ""):
        self.message = message
        self.module = module
        self.details = details
        super().__init__(self._format())

    def _format(self) -> str:
        base = f"[{self.module.upper()}] {self.message}"
        if self.details:
            base += f" — {self.details}"
        return base

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"module={self.module!r}, "
            f"details={self.details!r})"
        )


# ─────────────────────────────────────────────
# Autenticación y sesión
# ─────────────────────────────────────────────

class AuthError(LOBOError):
    """
    Fallo de autenticación.
    Ejemplos: contraseña incorrecta, usuario no encontrado en login.
    """

    def __init__(self, message: str = "Autenticación fallida.", details: str = ""):
        super().__init__(message, module="auth", details=details)


class SessionError(LOBOError):
    """
    Error relacionado con el estado de la sesión activa.
    Ejemplos: sesión no iniciada, operación que requiere admin.
    """

    def __init__(self, message: str = "Error de sesión.", details: str = ""):
        super().__init__(message, module="session", details=details)


class PermissionError(LOBOError):
    """
    El usuario no tiene permisos para ejecutar la operación.
    """

    def __init__(self, message: str = "Permisos insuficientes.", details: str = ""):
        super().__init__(message, module="auth", details=details)


# ─────────────────────────────────────────────
# Base de datos
# ─────────────────────────────────────────────

class DatabaseError(LOBOError):
    """
    Fallo en operaciones de base de datos.
    Ejemplos: commit fallido, conexión perdida, integridad violada.
    """

    def __init__(self, message: str = "Error en base de datos.", details: str = ""):
        super().__init__(message, module="db", details=details)


# ─────────────────────────────────────────────
# Módulos
# ─────────────────────────────────────────────

class ModuleError(LOBOError):
    """
    Error al cargar o ejecutar un módulo de LOBO.
    """

    def __init__(self, message: str = "Error en módulo.", module: str = "module", details: str = ""):
        super().__init__(message, module=module, details=details)


# ─────────────────────────────────────────────
# Validación de entrada
# ─────────────────────────────────────────────

class ValidationError(LOBOError):
    """
    Argumentos inválidos, formatos incorrectos o datos faltantes.
    Ejemplos: fecha mal formateada, campo obligatorio vacío.
    """

    def __init__(self, message: str = "Datos inválidos.", module: str = "validation", details: str = ""):
        super().__init__(message, module=module, details=details)


# ─────────────────────────────────────────────
# Recursos no encontrados
# ─────────────────────────────────────────────

class NotFoundError(LOBOError):
    """
    El recurso solicitado no existe en el sistema.
    Ejemplos: usuario no encontrado, evento inexistente, recordatorio eliminado.
    """

    def __init__(self, message: str = "Recurso no encontrado.", module: str = "core", details: str = ""):
        super().__init__(message, module=module, details=details)


# ─────────────────────────────────────────────
# Configuración
# ─────────────────────────────────────────────

class ConfigError(LOBOError):
    """
    Configuración faltante, inválida o incompatible.
    """

    def __init__(self, message: str = "Error de configuración.", details: str = ""):
        super().__init__(message, module="config", details=details)
