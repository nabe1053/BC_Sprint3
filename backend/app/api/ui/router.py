"""`/ui/*` ルーター。

画面が呼ぶ API を集約する（05-api-ipo.md 1章の A〜C・E〜G。特に F群 29〜37 の人の記録は
**必ずここに置く**。AGENT-01 のツールにはこの配下の API を一切渡さない）。

build-loop の Web スライスが endpoints/ 配下にモジュールを追加し、ここで include する。
"""

from fastapi import APIRouter

from app.api.ui.endpoints.agent_runs import router as run_router
from app.api.common.draft_validation import router as validation_router

from app.api.common.endpoints_reference import router as reference_router
from app.api.ui.endpoints import cases, documents
from app.api.ui.endpoints import records, versions, inventory, approvals, exports

router = APIRouter(prefix="/ui", tags=["ui"])

router.include_router(cases.router)
router.include_router(documents.router)
router.include_router(records.router)
router.include_router(approvals.router)
router.include_router(exports.router)
router.include_router(versions.router)
router.include_router(inventory.router)
# #4・#6・#7 は UI/AGENT 共通ハンドラ（05-api-ipo.md 0.3）。
router.include_router(reference_router)

# 次のスライスがここに endpoints を追加していく（例）:
# from app.api.ui.endpoints import edits, confirmations, ...
# router.include_router(edits.router)


router.include_router(run_router)
router.include_router(validation_router)
