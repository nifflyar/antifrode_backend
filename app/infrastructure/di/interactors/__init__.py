from dishka import Provider

from .auth import AuthInteractorProvider
from .user import UserInteractorProvider
from .audit import AuditInteractorProvider
from .etl import EtlProvider
from .upload import UploadInteractorProvider

interactor_providers: list[type[Provider]] = [
    AuthInteractorProvider,
    UserInteractorProvider,
    AuditInteractorProvider,
    EtlProvider,
    UploadInteractorProvider,
]

__all__ = [
    "AuthInteractorProvider",
    "UserInteractorProvider",
    "AuditInteractorProvider",
    "EtlProvider",
    "UploadInteractorProvider",
    "interactor_providers",
]
