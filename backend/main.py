"""Culinary Agent — Mobile API.

기존 services/, db/ 모듈을 그대로 재사용하여 모바일 앱(PWA/TWA)이 호출할 수 있는
HTTP 엔드포인트를 노출합니다. Streamlit 앱과 SQLite를 공유합니다.

라우트는 도메인별로 backend/routers/* 에 분리되어 있습니다.
- auth        : /auth/*               (회원가입/로그인/Google/me)
- ingredients : /ingredients/*, /scan
- recipes     : /recipes, /saved_recipes/*
- shopping    : /shopping/*

실행:
    cd culinary-agent
    uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

배포(Railway/Cloud Run):
    uvicorn backend.main:app --host 0.0.0.0 --port $PORT
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

from db.database import init_db  # noqa: E402
from backend.routers import auth as auth_router  # noqa: E402
from backend.routers import ingredients as ingredients_router  # noqa: E402
from backend.routers import posts as posts_router  # noqa: E402
from backend.routers import recipes as recipes_router  # noqa: E402
from backend.routers import shopping as shopping_router  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Culinary Agent API", version="0.2.0", lifespan=lifespan)

# CORS — 모바일 PWA·로컬 dev 모두 허용. 프로덕션에선 도메인 화이트리스트로 좁히세요.
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(anthropic.AuthenticationError)
async def anthropic_auth_handler(request: Request, exc: anthropic.AuthenticationError):
    return JSONResponse(
        status_code=401,
        content={
            "error": "anthropic_auth_failed",
            "message": ".env 파일의 ANTHROPIC_API_KEY가 유효하지 않습니다. "
                       "console.anthropic.com/settings/keys 에서 새 키를 발급받아 갱신하세요.",
            "detail": str(exc),
        },
    )


@app.exception_handler(anthropic.APIError)
async def anthropic_api_handler(request: Request, exc: anthropic.APIError):
    return JSONResponse(
        status_code=502,
        content={
            "error": "anthropic_api_error",
            "message": "Claude API 호출에 실패했습니다.",
            "detail": str(exc),
        },
    )


@app.get("/health")
def health():
    return {"status": "ok", "version": app.version}


app.include_router(auth_router.router)
app.include_router(ingredients_router.router)
app.include_router(recipes_router.router)
app.include_router(shopping_router.router)
app.include_router(posts_router.router)

# 게시판 첨부 이미지 정적 서빙. 디렉토리는 init 때 생성됨.
_UPLOADS_DIR = Path(__file__).resolve().parents[1] / "data" / "uploads"
_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_UPLOADS_DIR)), name="uploads")
