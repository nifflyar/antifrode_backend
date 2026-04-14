from dishka import Provider

from .auth import AuthInteractorProvider
from .user import UserInteractorProvider
from .audit import AuditInteractorProvider

interactor_providers: list[type[Provider]] = [
    AuthInteractorProvider,
    UserInteractorProvider,
    AuditInteractorProvider,
]

__all__ = [
    "AuthInteractorProvider",
    "UserInteractorProvider",
    "AuditInteractorProvider",
    "interactor_providers",
]
