class DomainError(Exception):
    """Error de negocio. La capa de presentacion lo traduce a HTTP."""


class NotFoundError(DomainError):
    """El recurso solicitado no existe."""


class ConflictError(DomainError):
    """La operacion choca con el estado actual del sistema."""


class ValidationError(DomainError):
    """Los datos recibidos no cumplen una regla de negocio."""
