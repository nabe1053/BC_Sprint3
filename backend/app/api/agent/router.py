"""`/agent/*` ルーター。

AGENT-01 のツールが呼ぶ API だけをここに集約する（05-api-ipo.md 7章のツール対応表・API番号
4・6・7・8・9・11・15〜21）。**人の記録 API（29〜37）は絶対にここへ置かない**
（05-api-ipo.md 7.1「境界はツール登録＋パス分離で守る」）。

build-loop のエージェントスライスが endpoints/ 配下にモジュールを追加し、ここで include する。
"""

from fastapi import APIRouter

from app.api.agent.endpoints.drafts import router as draft_router
from app.api.common.draft_validation import router as validation_router

from app.api.agent.endpoints import documents
from app.api.common.endpoints_reference import router as reference_router

router = APIRouter(prefix="/agent", tags=["agent"])

router.include_router(documents.router)
# #4・#6・#7 は UI/AGENT 共通ハンドラ（05-api-ipo.md 0.3）。
router.include_router(reference_router)

# 次のスライスがここに endpoints を追加していく（例）:
# from app.api.agent.endpoints import items, evidence, ...
# router.include_router(items.router)


router.include_router(draft_router)
router.include_router(validation_router)
