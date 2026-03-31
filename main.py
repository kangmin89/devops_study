from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import pipeline
import logging

# 기본 로깅 설정 (MLOps 운영 시 매우 중요합니다)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Korean Sentiment Analysis API",
    description="FastAPI를 활용한 한국어 감성분석 MLOps 파이프라인 테스트 서버입니다.",
    version="1.0.0"
)

# 다국어를 지원하는 사전학습된 파이프라인 모델을 로드합니다.
# 실제 운영 시에는 'beomi/kcbert-base' 등 한국어 특화 모델을 파인튜닝하여 사용하거나 S3 경로 등에서 로드하도록 고도화합니다.
MODEL_NAME = "nlptown/bert-base-multilingual-uncased-sentiment"

logger.info(f"Loading model '{MODEL_NAME}' ...")
try:
    sentiment_analyzer = pipeline("sentiment-analysis", model=MODEL_NAME)
    logger.info("Model loaded successfully.")
except Exception as e:
    logger.error(f"Failed to load model: {e}")
    sentiment_analyzer = None

class PredictionRequest(BaseModel):
    text: str

class PredictionResponse(BaseModel):
    label: str
    score: float

@app.get("/")
def health_check():
    """로드밸런서 또는 쿠버네티스(K8s)의 Readiness/Liveness 탐색용 엔드포인트"""
    status = "healthy" if sentiment_analyzer else "unhealthy"
    return {"status": status, "message": "MLOps Sentiment API Server is running."}

@app.post("/predict", response_model=PredictionResponse)
def predict_sentiment(request: PredictionRequest):
    if not sentiment_analyzer:
        raise HTTPException(status_code=503, detail="Model is currently unavailable. Please check the server logs.")
    
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="텍스트가 비어있습니다.")

    try:
        # 감성 분석 추론 실행
        # 반환 예시: [{'label': '5 stars', 'score': 0.85}]
        result = sentiment_analyzer(request.text)[0]
        
        return PredictionResponse(
            label=result['label'],
            score=float(result['score'])
        )
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail="추론 중 내부 서버 오류가 발생했습니다.")

if __name__ == "__main__":
    import uvicorn
    # 운영 환경에서는 workers 옵션을 늘리거나 Gunicorn 등을 함께 사용합니다.
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
