from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import os

from app.infrastructure.config import load_config
from app.infrastructure.container import setup_dishka_container
from dishka.integrations.fastapi import setup_dishka
from app.presentation.api.health.router import health_router
from app.presentation.api.auth.router import auth_router
from app.presentation.api.user.router import user_router
from app.presentation.api.audit.router import audit_router
from app.presentation.api.upload.router import upload_router
from app.presentation.api.scoring.router import scoring_router
from app.presentation.api.dashboard.router import dashboard_router
from app.presentation.api.passenger.router import passenger_router
from app.presentation.api.operations.router import operations_router
from app.presentation.api.risk.router import risk_router
from app.presentation.api.reports.router import reports_router
from app.presentation.api.middleware import AuthMiddleware

from app.presentation.api.exception import (
    validation_error_handler,
    application_error_handler,
    value_error_handler,
)
from app.application.common.exceptions import ApplicationError, ValidationError

logger = logging.getLogger(__name__)


async def create_initial_admin(container) -> None:
    """Create initial admin user if database is empty."""
    from app.domain.user.repository import IUserRepository
    from app.infrastructure.config import Config
    from app.application.auth.register import RegisterInteractor, RegisterInputDTO
    from app.application.common.transaction import TransactionManager

    try:
        async with container() as request_container:
            user_repo = await request_container.get(IUserRepository)
            config = await request_container.get(Config)
            transaction_manager = await request_container.get(TransactionManager)

            # Check if any users exist
            users_exist = await user_repo.any_users_exist()
            logger.info(f"Checking for existing users: {users_exist}")

            if users_exist:
                logger.info("Users already exist in database, skipping admin creation")
                return

            # Get admin emails from config
            admin_emails = config.auth.admin_emails
            logger.info(f"Admin emails from config: {admin_emails}")

            if not admin_emails:
                logger.warning("No admin emails configured, skipping admin creation")
                return

            # Create initial admin using the first configured admin email
            register_interactor = await request_container.get(RegisterInteractor)

            admin_email = admin_emails[0]
            # Get password from environment variable for secure operations
            default_password = os.environ.get("INITIAL_ADMIN_PASSWORD")
            logger.info(f"INITIAL_ADMIN_PASSWORD set: {bool(default_password)}")

            if not default_password:
                logger.warning(
                    f"INITIAL_ADMIN_PASSWORD environment variable not set. "
                    f"Please set it to create initial admin user for {admin_email}"
                )
                return

            try:
                result = await register_interactor(
                    RegisterInputDTO(
                        email=admin_email,
                        password=default_password,
                        full_name="Admin User",
                        actor_user_id=None,
                        is_admin=True,
                    )
                )
                await transaction_manager.commit()
                logger.info(f" Created initial admin user with email: {admin_email}")
                logger.info(f"  User ID: {result.user_id}")
            except Exception as e:
                logger.error(f"Could not create initial admin user: {e}", exc_info=True)
                await transaction_manager.rollback()
    except Exception as e:
        logger.error(f"Error in create_initial_admin: {e}", exc_info=True)


def create_app() -> FastAPI:
    config = load_config()

    app = FastAPI(title="Antifrode API")

    container = setup_dishka_container(config)
    setup_dishka(container, app)

    # Add authentication middleware FIRST (will be executed last)
    app.add_middleware(AuthMiddleware, config=config)

    # Add CORS middleware SECOND (will be executed first)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8000", "http://localhost:8001", "http://localhost:8080", "http://127.0.0.1:8000", "http://127.0.0.1:8001", "http://127.0.0.1:8080"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include all API routers FIRST with /api prefix
    app.include_router(health_router)
    app.include_router(auth_router, prefix="/api")
    app.include_router(user_router, prefix="/api")
    app.include_router(audit_router, prefix="/api")
    app.include_router(upload_router, prefix="/api")
    app.include_router(scoring_router, prefix="/api")
    app.include_router(dashboard_router, prefix="/api")
    app.include_router(passenger_router, prefix="/api")
    app.include_router(operations_router, prefix="/api")
    app.include_router(risk_router, prefix="/api")
    app.include_router(reports_router, prefix="/api")

    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(ApplicationError, application_error_handler)
    app.add_exception_handler(ValueError, value_error_handler)
    app.add_exception_handler(TypeError, value_error_handler)

    # Mount static files - AFTER all API routes to prevent catching API requests
    static_dir = os.path.join(os.path.dirname(__file__), "antifront-main/static")
    if os.path.isdir(static_dir):
        # Serve index.html at root for SPA
        @app.get("/")
        async def root():
            return FileResponse(os.path.join(static_dir, "index.html"))

        @app.get("/login.html")
        async def login():
            return FileResponse(os.path.join(static_dir, "login.html"))

        @app.get("/index.html")
        async def index():
            return FileResponse(os.path.join(static_dir, "index.html"))

        # Mount static files for CSS, JS, images at /static path
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.on_event("startup")
    async def startup_event() -> None:
        await create_initial_admin(container)

    return app


app = create_app()