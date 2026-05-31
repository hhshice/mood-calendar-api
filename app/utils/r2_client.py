"""Cloudflare R2 文件存储客户端

开发阶段优先使用本地存储；R2 凭证配齐后自动切换到 R2。
"""

import os
import uuid
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from app.config import settings

# 本地存储目录（开发阶段用）
LOCAL_UPLOAD_DIR = Path("uploads/images")
LOCAL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 允许的 MIME → 后缀映射
MIME_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


def is_r2_configured() -> bool:
    """检查 R2 是否已配置"""
    return bool(settings.r2_account_id and settings.r2_access_key_id and settings.r2_secret_access_key)


def _generate_filename(content_type: str) -> str:
    ext = MIME_EXT.get(content_type, ".bin")
    return f"{uuid.uuid4().hex}{ext}"


def get_r2_client():
    """获取 R2 S3 客户端"""
    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
    )


def upload_to_r2(file_data: bytes, filename: str, content_type: str) -> str:
    """上传到 Cloudflare R2，返回可公开访问的 URL"""
    client = get_r2_client()
    client.put_object(
        Bucket=settings.r2_bucket_name,
        Key=filename,
        Body=file_data,
        ContentType=content_type,
    )

    if settings.r2_public_url:
        return f"{settings.r2_public_url.rstrip('/')}/{filename}"
    # fallback: 使用 R2 设备域名
    return (
        f"https://{settings.r2_account_id}.r2.cloudflarestorage.com"
        f"/{settings.r2_bucket_name}/{filename}"
    )


def upload_to_local(file_data: bytes, filename: str) -> str:
    """保存到本地目录，返回相对路径"""
    filepath = LOCAL_UPLOAD_DIR / filename
    filepath.write_bytes(file_data)
    return f"/uploads/images/{filename}"


def upload_image(file_data: bytes, content_type: str) -> dict:
    """上传图片：优先 R2，其次本地，返回 { url, size }"""
    filename = _generate_filename(content_type)
    size = len(file_data)

    if is_r2_configured():
        try:
            url = upload_to_r2(file_data, filename, content_type)
            return {"url": url, "size": size}
        except (ClientError, NoCredentialsError):
            # R2 失败时回退到本地
            pass

    # 本地存储
    url = upload_to_local(file_data, filename)
    return {"url": url, "size": size}
