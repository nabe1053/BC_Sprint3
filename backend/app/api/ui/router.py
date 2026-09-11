"""`/ui/*` ルーター。

画面が呼ぶ API を集約する（05-api-ipo.md 1章の A〜C・E〜G。特に F群 29〜37 の人の記録は
**必ずここに置く**。AGENT-01 のツールにはこの配下の API を一切渡さない）。

build-loop の Web スライスが endpoints/ 配下にモジュールを追加し、ここで include する。
"""

from fastapi import APIRouter

router = APIRouter(prefix="/ui", tags=["ui"])

# build-loop がここに endpoints を追加していく（例）:
# from app.api.ui.endpoints import cases, edits, confirmations, ...
# router.include_router(cases.router)
