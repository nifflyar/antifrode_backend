from dishka import Provider

from .auth import AuthInteractorProvider
from .user import UserInteractorProvider
from .audit import AuditInteractorProvider
from .etl import EtlProvider
from .upload import UploadInteractorProvider
from .scoring import ScoringProvider
from .dashboard import DashboardInteractorProvider
from .passenger import PassengerInteractorProvider

interactor_providers: list[type[Provider]] = [
    AuthInteractorProvider,
    UserInteractorProvider,
    AuditInteractorProvider,
    EtlProvider,
    UploadInteractorProvider,
    ScoringProvider,
    DashboardInteractorProvider,
    PassengerInteractorProvider,
]

__all__ = [
    "AuthInteractorProvider",
    "UserInteractorProvider",
    "AuditInteractorProvider",
    "EtlProvider",
    "UploadInteractorProvider",
    "ScoringProvider",
    "DashboardInteractorProvider",
    "PassengerInteractorProvider",
    "interactor_providers",
]
