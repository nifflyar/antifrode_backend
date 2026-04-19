import logging
import asyncio
from typing import Annotated

from fastapi import APIRouter, File, Request, UploadFile, HTTPException, status, Query, BackgroundTasks
from dishka.integrations.fastapi import FromDishka, inject
from dishka import AsyncContainer

from app.application.upload.create_upload import CreateUploadInputDTO, CreateUploadInteractor
from app.application.upload.get_upload import GetUploadInputDTO, GetUploadInteractor
from app.application.upload.list_uploads import ListUploadsInputDTO, ListUploadsInteractor
from app.application.etl.pipeline import EtlPipeline
from app.infrastructure.config import Config
from app.presentation.api.security import get_optional_auth_claims_from_request
from app.presentation.api.upload.schemas import UploadListResponse, UploadResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/excel", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
@inject
async def upload_excel(
    request: Request,
    background_tasks: BackgroundTasks,
    config: FromDishka[Config],
    create_upload: FromDishka[CreateUploadInteractor],
    file: UploadFile = File(...),
) -> UploadResponse:
    """Загрузить Excel-файл с транзакциями для ETL-пайплайна."""
    claims = get_optional_auth_claims_from_request(request, config)
    if not claims:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    filename = file.filename or "unknown.xlsx"
    if not filename.endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Только файлы .xlsx поддерживаются"
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Файл пуст")

    # 1. Создаем запись о загрузке со статусом PENDING
    upload_dto = await create_upload(
        CreateUploadInputDTO(
            filename=filename,
            filepath=f"in_memory://{file.filename}",
            user_id=claims.user_id,
        )
    )

    root_container: AsyncContainer = request.app.state.dishka_container

    # 2. Обернем вызов ETL в функцию для BackgroundTask
    async def run_etl_task(upload_id: int, data: bytes, user_id):
        logger.info(f"Начинается фоновая обработка файла (upload_id={upload_id})")
        try:
            async with root_container() as task_container:
                etl_pipeline = await task_container.get(EtlPipeline)
                # Запускаем оркестратор
                await etl_pipeline.run(upload_id=upload_id, file_bytes=data, user_id=user_id)
        except Exception as e:
             logger.exception(f"Критическая ошибка при фоновой обработке файла: {e}")

    # 3. Добавляем задачу в фон (чтобы не блокировать HTTP-ответ)
    background_tasks.add_task(
        run_etl_task,
        upload_id=upload_dto.id,
        data=file_bytes,
        user_id=claims.user_id
    )

    return UploadResponse(
        id=str(upload_dto.id),
        filename=upload_dto.filename,
        status=upload_dto.status,
        uploaded_at=str(upload_dto.uploaded_at),
        uploaded_by_user_id=str(claims.user_id.value) if claims.user_id else None,
    )


@router.get("", response_model=UploadListResponse)
@inject
async def list_uploads(
    request: Request,
    config: FromDishka[Config],
    list_interactor: FromDishka[ListUploadsInteractor],
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> UploadListResponse:
    """Получить список всех загрузок (с пагинацией)."""
    claims = get_optional_auth_claims_from_request(request, config)
    if not claims:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    result = await list_interactor(ListUploadsInputDTO(limit=limit, offset=offset))

    # count_all мы пока не реализовали для Upload, 
    # поэтому просто вернем размер текущего батча + offset как заглушку, 
    # либо нужно дописать count в IUploadRepository
    return UploadListResponse(
        items=[
            UploadResponse(
                id=str(item.id),
                filename=item.filename,
                status=item.status,
                uploaded_at=str(item.uploaded_at),
                uploaded_by_user_id=str(item.uploaded_by_user_id) if item.uploaded_by_user_id else None,
            )
            for item in result.items
        ],
        total=len(result.items) + offset, # заглушка для total
        limit=result.limit,
        offset=result.offset,
    )


@router.get("/{upload_id}", response_model=UploadResponse)
@inject
async def get_upload(
    upload_id: int,
    request: Request,
    config: FromDishka[Config],
    get_interactor: FromDishka[GetUploadInteractor],
) -> UploadResponse:
    """Получить статус конкретной загрузки."""
    claims = get_optional_auth_claims_from_request(request, config)
    if not claims:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        result = await get_interactor(GetUploadInputDTO(upload_id=upload_id))
        return UploadResponse(
            id=str(result.id),
            filename=result.filename,
            status=result.status,
            uploaded_at=str(result.uploaded_at),
            uploaded_by_user_id=str(result.uploaded_by_user_id) if result.uploaded_by_user_id else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

upload_router = router
