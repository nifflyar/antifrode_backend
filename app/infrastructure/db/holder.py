from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.repos import RefreshSessionRepositoryImpl, UserRepositoryImpl, AuditLogRepositoryImpl


class HolderDao:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepositoryImpl(session)
        self.refresh_session_repo = RefreshSessionRepositoryImpl(session)
        self.audit_log_repo = AuditLogRepositoryImpl(session)

