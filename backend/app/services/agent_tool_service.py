"""The thirteen tool operations delegate persistence to a scoped repository."""
from dataclasses import asdict

from app.domain.draft_errors import DraftError
from app.services.draft_service import DraftService


class AgentToolService:
    def __init__(self, context, repository):
        self.context = context
        self.repository = repository
        self.drafts = DraftService(repository)

    async def execute(self, name, args):
        repo, version = self.repository, self.context.version_id
        if name == "list_case_documents":
            return await repo.list_documents()
        if name == "read_document":
            return await repo.read_document(
                args.document_id, args.from_seq, args.to_seq
            )
        if name == "read_email":
            return await repo.read_email(args.document_id)
        if name == "search_documents":
            if not args.query.strip():
                raise DraftError("E_QUERY_REQUIRED", "検索語を指定してください")
            return await repo.search(args.query, args.limit)
        if name == "get_rules":
            return await repo.get_rules()
        if name == "report_unreadable":
            if not args.detail.strip():
                raise DraftError("E_DETAIL_REQUIRED", "説明を指定してください")
            return await repo.report_unreadable(args)
        if name == "record_case_header":
            row = await self.drafts.save_header(version, args.header)
            return {"header_id": row.id}
        if name == "propose_items":
            rows = await self.drafts.add_items(version, args.rows)
            return {
                "items": [{"item_id": r.id, "row_code": r.row_code} for r in rows],
                "rejected": [],
            }
        if name == "record_evidence":
            rows = await self.drafts.add_evidences(version, args.evidences)
            return {"evidences": [{"evidence_id": row.id} for row in rows]}
        if name == "record_question":
            rows = await self.drafts.add_questions(version, args.questions)
            return {"questions": [{"question_id": row.id} for row in rows]}
        if name == "record_source_inventory":
            rows = await self.drafts.add_inventory(version, args.entries)
            return {"entries": [{"entry_id": r.id} for r in rows]}
        if name == "validate_draft":
            return asdict(await self.drafts.validate(version))
        if name == "finalize_draft":
            result = await self.drafts.finalize(version)
            return {
                "version_id": result.id,
                "current_state": result.current_state,
                "is_complete": result.is_complete,
            }
        raise DraftError("E_REQUEST_INVALID", "未登録のツールです")
