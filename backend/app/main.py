"""
FastAPI application for InfiniteQ planning harness.
"""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.services.vultr_client import VultrClient
from app.services.model_registry import ModelRegistry
from app.services.session_manager import SessionManager
from app.services.question_engine import QuestionEngine
from app.services.plan_reducer import PlanReducer
from app.services.plan_synthesizer import PlanSynthesizer
from app.services.reflection_service import ReflectionService
from app.api.routes import router, init_routes

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Rate limiting configuration
RATE_LIMIT_DEFAULT = os.environ.get("RATE_LIMIT_DEFAULT", "60/minute")
RATE_LIMIT_SESSION = os.environ.get("RATE_LIMIT_SESSION", "10/minute")
RATE_LIMIT_LLM = os.environ.get("RATE_LIMIT_LLM", "30/minute")

limiter = Limiter(key_func=get_remote_address)

# Global services
vultr_client: VultrClient = None
model_registry: ModelRegistry = None
session_manager: SessionManager = None
question_engine: QuestionEngine = None
plan_reducer: PlanReducer = None
plan_synthesizer: PlanSynthesizer = None
reflection_service: ReflectionService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Initializes services on startup.
    """
    global vultr_client, model_registry, session_manager
    global question_engine, plan_reducer, plan_synthesizer, reflection_service

    logger.info("Starting InfiniteQ application...")

    try:
        # Initialize Vultr client
        api_key = os.environ.get("VULTR_INFERENCE_API_KEY")
        if not api_key:
            logger.error("VULTR_INFERENCE_API_KEY not set!")
            raise ValueError("VULTR_INFERENCE_API_KEY environment variable required")

        vultr_client = VultrClient(api_key=api_key)
        logger.info("Vultr client initialized")

        # Initialize model registry and discover models
        model_registry = ModelRegistry(vultr_client)
        models = model_registry.discover_models()
        logger.info(f"Discovered {len(models)} models")

        # Initialize services
        session_manager = SessionManager(vultr_client, model_registry)
        question_engine = QuestionEngine(vultr_client, model_registry)
        plan_reducer = PlanReducer(vultr_client, model_registry)
        plan_synthesizer = PlanSynthesizer(vultr_client, model_registry)
        reflection_service = ReflectionService(vultr_client, model_registry)
        logger.info("Reflection service initialized")

        # Initialize routes
        init_routes(
            session_manager=session_manager,
            question_engine=question_engine,
            plan_reducer=plan_reducer,
            plan_synthesizer=plan_synthesizer,
            reflection_service=reflection_service
        )

        logger.info("All services initialized successfully")

        yield

        logger.info("Shutting down InfiniteQ application...")

    except Exception as e:
        logger.error(f"Failed to initialize application: {e}", exc_info=True)
        raise


# Create FastAPI app
app = FastAPI(
    title="InfiniteQ Planning Harness",
    description="AI-powered project planning via multi-model interview",
    version="1.0.0",
    lifespan=lifespan
)

# Add rate limiter to app state and exception handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration - use environment variable for allowed origins
ALLOWED_ORIGINS = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
)

# Include routes
app.include_router(router, prefix="/api/v1", tags=["planning"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "InfiniteQ Planning Harness",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "models_available": len(model_registry.get_all_models()) if model_registry else 0
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    debug_mode = os.environ.get("DEBUG", "false").lower() == "true"
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=debug_mode,  # Only enable reload in debug mode
        log_level="debug" if debug_mode else "info"
    )
