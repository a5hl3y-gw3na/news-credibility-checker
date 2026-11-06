import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app import analysis
from app.schemas import AnalysisResponse, ArticleRequest
from app.services import model_service


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        model_service.load_model()
        logging.info("AI model loaded successfully.")
    except Exception:
        logging.exception("Failed to load AI model.")
        raise

    yield

app = FastAPI(title="News Credibility Checker API", description="AI-powered assessment of online news credibility.",
              version="0.1.0", lifespan=lifespan)

# Lets the browser extension call the API. Tighten extension ID before the demo.
# Restrict extension origins to the actual extension ID before demonstration.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"(chrome-extension|moz-extension)://.*|http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": model_service.is_loaded()}

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(req: ArticleRequest):
    """
       Analyse an article and return its credibility assessment.
       Article contents should not be persistently stored.
    """
    return await analysis.run(req)

