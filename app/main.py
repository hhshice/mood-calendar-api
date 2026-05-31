from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.exceptions import AppException
from app.routers import auth, calendar, mood, comment, upload


@asynccontextmanager
async def lifespan(application: FastAPI):
    """启动时自动创建表结构（开发阶段用，上线后改用 Alembic）"""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="心情日历 API",
    description="心情日历微信小程序后端接口",
    version="0.1.0",
    docs_url="/docs",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── 全局异常处理器 ───────────────────────


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """统一处理应用级异常"""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """兜底：未预料到的异常"""
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "服务器内部错误，请稍后重试",
            }
        },
    )


# ─── 注册路由 ─────────────────────────────

app.include_router(auth.router)
app.include_router(calendar.router)
app.include_router(mood.router)
app.include_router(comment.router)
app.include_router(upload.router)

# ─── 本地上传文件静态目录 ──────────────────
from pathlib import Path

UPLOAD_DIR = Path("uploads/images")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads/images", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


# ─── 健康检查 ─────────────────────────────


@app.get("/health")
def health_check():
    return {"status": "ok", "version": "0.1.0"}
