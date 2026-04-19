import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
import logging
from processor import ScoringProcessor

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Antifrode ML Service")

# Конфигурация
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@postgres:5432/antifrode_backend_db")
processor = ScoringProcessor(DATABASE_URL)

class ScoringRequest(BaseModel):
    upload_id: int

class ScoringResult(BaseModel):
    passenger_id: int
    rule_score: float
    ml_score: float
    final_score: float
    risk_band: str
    top_reasons: List[str]
    # Признаки (для сохранения в passenger_features)
    total_tickets: int
    refund_cnt: int
    refund_share: float
    night_tickets: int
    night_share: float
    late_refunds: int
    refund_close_ratio: float
    fake_fio: float

class ScoringResponse(BaseModel):
    upload_id: int
    status: str
    results: Optional[List[ScoringResult]] = None

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/score", response_model=ScoringResponse)
async def score_upload(request: ScoringRequest):
    """Запускает процесс скоринга для загруженного файла."""
    logger.info(f"Starting scoring for upload_id={request.upload_id}")
    
    try:
        results = await processor.process(request.upload_id)
        
        if not results:
            return ScoringResponse(
                upload_id=request.upload_id,
                status="no_data",
                results=[]
            )
            
        return ScoringResponse(
            upload_id=request.upload_id,
            status="success",
            results=results
        )
        
    except Exception as e:
        logger.exception(f"Error during scoring upload_id={request.upload_id}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
