"""Run admission policy and jobs dispatch; no SQL or HTTP dependencies."""
from app.domain.draft_errors import DraftError
from app.domain.run_types import RunResult
from app.agent import definition


class RunService:
    def __init__(
        self,
        repository,
        *,
        limits,
        input_limits,
        scheduler,
        external=False,
        model=None,
    ):
        self.repository = repository
        self.limits = limits
        self.input_limits = input_limits
        self.scheduler = scheduler
        self.external = external
        self.model = model

    def _validate_input(self, docs, readable, file_size):
        limits = self.input_limits

        def check(kind, actual, limit, document_id=None):
            if actual > limit:
                details = {"kind": kind, "actual": actual, "limit": limit}
                if document_id is not None:
                    details["documentId"] = document_id
                raise DraftError("E_LIMIT_EXCEEDED", "入力上限を超えています", details)

        check("documents", len(docs), limits.max_documents)
        for doc in docs:
            size = file_size(doc)
            # Intake already checked original size. Extracted content is reusable.
            if size is not None:
                check("fileBytes", size, limits.max_file_bytes, doc.id)
            if doc.page_count is not None and doc.kind in ("pdf", "xlsx"):
                check(
                    "pdfPages" if doc.kind == "pdf" else "xlsxSheets",
                    doc.page_count,
                    limits.max_pdf_pages
                    if doc.kind == "pdf"
                    else limits.max_xlsx_sheets,
                    doc.id,
                )
        if not readable:
            raise DraftError("E_NO_READABLE_DOCUMENT", "読取可能な資料がありません")

    async def start(self, case_id, rule_version=None, acknowledged_carry_over=False):
        if self.external:
            raise DraftError(
                "E_EXTERNAL_SEND_NOT_APPROVED", "実モデルが構成されていません"
            )
        await self.repository.recover_expired(case_id=case_id)
        run = await self.repository.reserve(
            case_id,
            None if rule_version == "current" else rule_version,
            acknowledged_carry_over,
            self.limits.snapshot(),
            self._validate_input,
            definition.LOCAL_IMPL_VERSION,
            model=self.model if self.model is not None else definition.DUMMY_MODEL_ID,
        )
        if run.outcome != "running":
            raise DraftError("E_JOB_START_FAILED", "実行トレースを保存できませんでした")
        try:
            self.scheduler(run)
        except Exception as exc:
            await self.repository.finish(
                run.id, RunResult("failed", detail="job_start_failed")
            )
            raise DraftError(
                "E_JOB_START_FAILED", "実行を開始できませんでした"
            ) from exc
        return run

    async def active_run(self, case_id):
        """画面を離れた後も進捗表示へ戻るための、案件の実行中 run（TEST-04 #1）。

        期限切れの running は先に回収する（再起動で取り残された run に復帰させると、
        起動ボタンが「準備中」のまま解除経路を失う。start と同じ回収を通す）。
        """
        await self.repository.recover_expired(case_id=case_id)
        return await self.repository.active_run_id(case_id)

    async def progress(self, run_id):
        return await self.repository.progress(run_id)

    async def steps(self, run_id):
        return await self.repository.steps(run_id)
