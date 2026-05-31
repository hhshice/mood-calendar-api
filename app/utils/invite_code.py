import secrets
import string


def generate_invite_code(length: int = 6) -> str:
    """生成随机邀请码（大写字母+数字）"""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))
