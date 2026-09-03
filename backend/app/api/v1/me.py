from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.auth import MenuItem, MeResponse

router = APIRouter(tags=["me"])


@router.get("/me", response_model=MeResponse)
async def me(user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(user_id=user.id, username=user.username, display_name=user.display_name, role=user.role, avatar_url=user.avatar_url, last_login=user.last_login)


@router.get("/me/menus", response_model=list[MenuItem])
async def menus(user: User = Depends(get_current_user)) -> list[MenuItem]:
    common = [
        MenuItem(name="realtime", label="实时检测", path="/realtime", roles=["admin", "operator"]),
        MenuItem(name="history", label="历史记录", path="/history", roles=["admin", "operator"]),
        MenuItem(name="analytics", label="统计分析", path="/analytics", roles=["admin", "operator"]),
    ]
    if user.role == "admin":
        common.extend([
            MenuItem(name="config", label="参数配置", path="/config", roles=["admin"]),
            MenuItem(name="system", label="系统管理", path="/system", roles=["admin"]),
        ])
    return common
