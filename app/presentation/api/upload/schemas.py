from typing import List, Optional
from pydantic import BaseModel


class UploadResponse(BaseModel):
    id: int
    filename: str
    status: str
    uploaded_at: str
    uploaded_by_user_id: Optional[int]


class UploadListResponse(BaseModel):
    items: List[UploadResponse]
    total: int
    limit: int
    offset: int
