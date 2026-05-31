from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from fastapi.responses import FileResponse

from app.dependencies import get_current_user
from app.exceptions import FileTooLarge, InvalidFileType
from app.models.user import User
from app.utils.r2_client import upload_image, LOCAL_UPLOAD_DIR

router = APIRouter(prefix="/api/upload", tags=["文件"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/image", response_model=dict, status_code=status.HTTP_201_CREATED)
async def upload_image_endpoint(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_TYPES:
        raise InvalidFileType()

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise FileTooLarge()

    result = upload_image(contents, file.content_type)
    return {"data": result}


# 本地存储的图片可直接通过此路由访问
@router.get("/images/{filename}")
async def serve_image(filename: str):
    filepath = LOCAL_UPLOAD_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="图片不存在")
    return FileResponse(str(filepath))


