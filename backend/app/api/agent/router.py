"""`/agent/*` ルーター。

AGENT-01 のツールが呼ぶ API だけをここに集約する（05-api-ipo.md 7章のツール対応表・API番号
4・6・7・8・9・11・15〜21）。**人の記録 API（29〜37）は絶対にここへ置かない**
（05-api-ipo.md 7.1「境界はツール登録＋パス分離で守る」）。

build-loop のエージェントスライスが endpoints/ 配下にモジュールを追加し、ここで include する。
"""

from fastapi import APIRouter

router = APIRouter(prefix="/agent", tags=["agent"])

# build-loop がここに endpoints を追加していく（例）:
# from app.api.agent.endpoints import documents, items, evidence, ...
# router.include_router(documents.router)
