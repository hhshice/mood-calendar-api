from fastapi import HTTPException, status


class AppException(HTTPException):
    """应用级异常基类"""

    def __init__(self, code: str, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.code = code
        self.message = message
        super().__init__(status_code=status_code, detail=self.to_dict())

    def to_dict(self) -> dict:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
            }
        }


class InvalidInviteCode(AppException):
    def __init__(self):
        super().__init__(
            code="INVALID_INVITE_CODE",
            message="邀请码无效，请确认后重试",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class AlreadyMember(AppException):
    def __init__(self):
        super().__init__(
            code="ALREADY_MEMBER",
            message="你已经是该日历的成员了",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class CalendarFull(AppException):
    def __init__(self):
        super().__init__(
            code="CALENDAR_FULL",
            message="该日历已满员（最多4人）",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class EntryAlreadyExists(AppException):
    def __init__(self):
        super().__init__(
            code="ENTRY_ALREADY_EXISTS",
            message="今天已经记录过心情了",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class NotAuthorized(AppException):
    def __init__(self, message: str = "只有创建者才能执行此操作"):
        super().__init__(
            code="NOT_AUTHORIZED",
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class NotMember(AppException):
    def __init__(self):
        super().__init__(
            code="NOT_MEMBER",
            message="你不是该日历的成员",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class NotFound(AppException):
    def __init__(self, entity: str = "资源"):
        super().__init__(
            code="NOT_FOUND",
            message=f"{entity}不存在",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class InvalidFileType(AppException):
    def __init__(self):
        super().__init__(
            code="INVALID_FORMAT",
            message="不支持的图片格式，仅支持 jpg/png/gif/webp",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class FileTooLarge(AppException):
    def __init__(self):
        super().__init__(
            code="FILE_TOO_LARGE",
            message="文件大小超过 10MB 限制",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class SelfRemoveNotAllowed(AppException):
    def __init__(self):
        super().__init__(
            code="SELF_REMOVE_NOT_ALLOWED",
            message="不能移除自己",
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class CreatorCannotLeave(AppException):
    def __init__(self):
        super().__init__(
            code="CREATOR_CANNOT_LEAVE",
            message="创建者不能退出日历，请使用解散功能",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
