"""微信小程序 API 客户端"""

import json
import logging
from urllib.request import urlopen, Request

from app.config import settings

logger = logging.getLogger(__name__)

WECHAT_CODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"


def _is_configured() -> bool:
    """检查微信凭证是否已真实配置（非占位符）"""
    app_id = settings.wechat_app_id
    secret = settings.wechat_app_secret
    if not app_id or not secret:
        return False
    # 真实 AppID 以 wx 开头后跟 16 位十六进制字符，长度 18
    if app_id == "wx_placeholder" or len(app_id) < 16:
        return False
    return True


def code2session(code: str) -> dict:
    """
    用微信登录 code 换取 openid 和 session_key

    文档：https://developers.weixin.qq.com/miniprogram/dev/OpenApiDoc/user-login/code2Session.html

    返回示例（成功）：
        {"openid": "xxx", "session_key": "xxx"}

    返回示例（失败）：
        {"errcode": 40029, "errmsg": "invalid code"}

    返回示例（配置为空时）：
        {"openid": "mock_openid_xxx", "session_key": ""}
    """
    # 开发模式：未配置微信凭证时使用 mock
    if not _is_configured():
        logger.warning("微信 AppID/Secret 未配置或为占位符，使用 mock openid")
        return {"openid": f"mock_openid_{code[:8]}", "session_key": ""}

    params = (
        f"appid={settings.wechat_app_id}"
        f"&secret={settings.wechat_app_secret}"
        f"&js_code={code}"
        f"&grant_type=authorization_code"
    )
    url = f"{WECHAT_CODE2SESSION_URL}?{params}"

    try:
        req = Request(url)
        with urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.error(f"微信 code2Session 请求失败: {e}")
        raise ValueError(f"微信登录验证失败: {e}")

    # 检查微信返回的错误码
    if "errcode" in body and body["errcode"] != 0:
        errcode = body["errcode"]
        errmsg = body.get("errmsg", "未知错误")
        logger.error(f"微信 code2Session 返回错误: errcode={errcode}, errmsg={errmsg}")
        raise ValueError(f"微信登录验证失败 ({errcode}: {errmsg})")

    if "openid" not in body:
        logger.error(f"微信 code2Session 返回缺少 openid: {body}")
        raise ValueError("微信登录验证失败：未获取到 openid")

    return body
