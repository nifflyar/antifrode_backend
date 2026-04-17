from dishka import Provider

from .auth import AuthInteractorProvider
from .user import UserInteractorProvider
from .audit import AuditInteractorProvider
from .etl import EtlProvider
from .upload import UploadInteractorProvider
from .scoring import ScoringInteractorProvider
from .dashboard import DashboardInteractorProvider

interactor_providers: list[type[Provider]] = [
    AuthInteractorProvider,
    UserInteractorProvider,
    AuditInteractorProvider,
    EtlProvider,
    UploadInteractorProvider,
    ScoringInteractorProvider,
    DashboardInteractorProvider,
]

__all__ = [
    "AuthInteractorProvider",
    "UserInteractorProvider",
    "AuditInteractorProvider",
    "EtlProvider",
    "UploadInteractorProvider",
    "ScoringInteractorProvider",
    "DashboardInteractorProvider",
    "interactor_providers",
]
