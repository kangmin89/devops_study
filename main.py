from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from transformers import pipeline
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Korean Sentiment Analysis API",
    description="FastAPI를 활용한 한국어 감성분석 MLOps 파이프라인 (Blue-Green 배포 버전)",
    version="2.0.0"
)

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

@app.get("/", response_class=HTMLResponse)
def get_gui():
    return """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>MLOps 감성 분석기 (v2)</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gradient-to-br from-indigo-100 to-purple-100 flex items-center justify-center min-h-screen">
        <div class="bg-white p-8 rounded-xl shadow-2xl w-full max-w-lg transition-all duration-300 hover:shadow-purple-200">
            <h1 class="text-3xl font-extrabold mb-2 text-center text-transparent bg-clip-text bg-gradient-to-r from-purple-600 to-blue-500">한국어 감성 분석 AI</h1>
            <p class="text-center text-gray-500 mb-6 text-sm">v2.0 UI (Blue-Green Deployment)</p>
            
            <textarea id="textInput" class="w-full border-2 border-purple-100 p-4 rounded-lg mb-4 focus:outline-none focus:border-purple-400 focus:ring-1 focus:ring-purple-400 transition" rows="4" placeholder="분석할 한국어 문장을 입력해 보세요 (예: MLOps 시스템 정말 최고야!)..."></textarea>
            
            <button onclick="predict()" class="w-full bg-gradient-to-r from-purple-600 to-blue-500 text-white font-bold py-3 px-4 rounded-lg hover:from-purple-700 hover:to-blue-600 focus:outline-none focus:shadow-outline transform hover:-translate-y-0.5 transition duration-150 ease-in-out">
                감성 분석 실행
            </button>
            
            <div id="result" class="mt-6 p-4 rounded-lg hidden border">
                <div class="flex items-center justify-between">
                    <span class="text-gray-600 font-semibold text-lg" id="resLabel"></span>
                    <span class="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-sm font-bold" id="resScore"></span>
                </div>
            </div>
            <div id="error" class="mt-4 p-4 bg-red-50 text-red-600 rounded-lg hidden text-sm"></div>
        </div>

        <script>
            async function predict() {
                const text = document.getElementById('textInput').value;
                const resultDiv = document.getElementById('result');
                const errorDiv = document.getElementById('error');
                
                resultDiv.classList.add('hidden');
                errorDiv.classList.add('hidden');
                
                if (!text.trim()) {
                    errorDiv.innerText = "텍스트를 입력해주세요!";
                    errorDiv.classList.remove('hidden');
                    return;
                }

                try {
                    const response = await fetch('/predict', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ text })
                    });
                    
                    const data = await response.json();
                    
                    if(response.ok) {
                        document.getElementById('resLabel').innerText = `결과: ${data.label}`;
                        document.getElementById('resScore').innerText = `신뢰도: ${(data.score * 100).toFixed(1)}%`;
                        resultDiv.classList.remove('hidden');
                        resultDiv.classList.add('bg-purple-50', 'border-purple-200');
                    } else {
                        errorDiv.innerText = `오류: ${data.detail || JSON.stringify(data)}`;
                        errorDiv.classList.remove('hidden');
                    }
                } catch (e) {
                    errorDiv.innerText = `서버 연결 오류: ${e.message}`;
                    errorDiv.classList.remove('hidden');
                }
            }
        </script>
    </body>
    </html>
    """

# Docker Container의 Liveness/Readiness 탐색을 위한 Endpoint로 분리
@app.get("/health")
def health_check():
    status = "healthy" if sentiment_analyzer else "unhealthy"
    return {"status": status}

@app.post("/predict", response_model=PredictionResponse)
def predict_sentiment(request: PredictionRequest):
    if not sentiment_analyzer:
        raise HTTPException(status_code=503, detail="Model unavailable")
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="텍스트가 비어있습니다.")
    try:
        result = sentiment_analyzer(request.text)[0]
        return PredictionResponse(label=result['label'], score=float(result['score']))
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail="추론 실패")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
