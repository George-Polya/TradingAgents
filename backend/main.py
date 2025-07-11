from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from utils.database import create_db_and_tables
from utils.containers import Container
from utils.middlewares import RateLimitMiddleware, LoggingMiddleware, SecurityHeadersMiddleware
from utils.exceptions import BaseAPIException
from contextlib import asynccontextmanager
from datetime import datetime

from analysis.interface.controller.analysis_controller import router as analysis_router
from member.interface.controller.member_controller import router as member_router
import logging
from utils.logger import setup_logging
from config.config import get_settings

setup_logging()
settings = get_settings()

# 라이프사이클 관리
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger = logging.getLogger(__name__)
    # 시작 시
    logger.info("🚀 FastAPI 애플리케이션 시작")
    create_db_and_tables()
    logger.info("📊 데이터베이스 초기화 완료")
    
    # WebSocket manager background tasks 시작
    websocket_manager = app.container.websocket_manager()
    await websocket_manager.start_background_tasks()
    logger.info("🔌 WebSocket 보안 태스크 시작")
    
    yield
    
    # 종료 시
    logger.info("🔄 애플리케이션 종료")
    await websocket_manager.stop_background_tasks()
    logger.info("🔌 WebSocket 보안 태스크 종료")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan
)

# 컨테이너 설정
app.container = Container()

# 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 신뢰할 수 있는 호스트 설정
if settings.is_production:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["tradingagents.com", "*.tradingagents.com"])

# 커스텀 미들웨어 추가
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    RateLimitMiddleware, 
    requests_per_minute=settings.RATE_LIMIT_REQUESTS,
    period=settings.RATE_LIMIT_PERIOD
)

# 글로벌 예외 처리기
@app.exception_handler(BaseAPIException)
async def api_exception_handler(request: Request, exc: BaseAPIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.detail,
                "path": str(request.url)
            }
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "path": str(request.url)
            }
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger = logging.getLogger(__name__)
    logger.error(f"예상치 못한 오류: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Internal server error" if settings.is_production else str(exc),
                "path": str(request.url)
            }
        }
    )

# 라우터 등록
app.include_router(analysis_router, prefix=settings.API_V1_STR)
app.include_router(member_router, prefix=settings.API_V1_STR)

# 헬스 체크 엔드포인트
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.get("/")
async def root():
    logger = logging.getLogger(__name__)
    logger.info("📍 루트 엔드포인트 호출됨")
    return {
        "message": "Trading Agents API",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "docs_url": "/docs"
    }