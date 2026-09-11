"""API #1〜#3 案件（05-api-ipo.md 1章 A・5章の要約・3章にはこの3本の詳細記述は無い）。

対象パス（0.3・区分 UI）:
    POST /api/v1/ui/cases
    GET  /api/v1/ui/cases
    GET  /api/v1/ui/cases/{caseId}

期待するレスポンス契約（本テストの前提。orval スキーマが SSOT になる前段階の仮決め。
実装者が別名を採用する場合は本テストと合わせて調整すること）:
    POST 201: {"caseId": <int>, "caseCode": <str>, "customerName": <str|None>,
               "title": <str|None>, "createdAt": <ISO8601 str>}
    GET (list) 200: {"cases": [{"caseId": ..., "caseCode": ...,
               "progressStatus": "intake" | "draft_review" | "staff_checked" | "review_checked",
               ...}]}
        - 進捗ステータスの導出元は 05-api-ipo.md 5章「1 の進捗ステータスの導出元」。
          T-102 時点では版（versions）を作る手段が無いため、
          「版が無い案件は progressStatus == 'intake'（①資料投入）」だけを検証する。
          ②③④（版がある場合）は versions の Repository ができる T-201 以降で追加する
          （orchestrator 指示どおり）。
    GET (detail) 200: {"caseId": ..., "caseCode": ..., "customerName": ..., "title": ...}
"""

CASES_PATH = "/api/v1/ui/cases"


def test_create_case_returns_201_with_case_id(client) -> None:
    """正常系: 案件を作成すると 201 と caseId が返る。"""
    response = client.post(
        CASES_PATH,
        json={
            "caseCode": "CASE-101",
            "customerName": "双葉物産",
            "title": "羽島沖ガス田",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["caseId"], int)
    assert body["caseCode"] == "CASE-101"


def test_create_case_rejects_empty_case_code_with_422(client) -> None:
    """異常系: caseCode が空文字は Pydantic バリデーションで 422（決定5）。"""
    response = client.post(
        CASES_PATH, json={"caseCode": "", "customerName": None, "title": None}
    )

    assert response.status_code == 422


def test_create_case_rejects_whitespace_only_case_code_with_422(client) -> None:
    """異常系: caseCode が空白のみ（"   "）は 422（reviewer 指摘 重-2）。

    以前は Service の ValueError がハンドラを持たず 500 になっていた。
    Pydantic の `StringConstraints(strip_whitespace=True, min_length=1)` で
    422 に寄せる（決定5と整合）。"""
    response = client.post(
        CASES_PATH, json={"caseCode": "   ", "customerName": None, "title": None}
    )

    assert response.status_code == 422


def test_create_case_rejects_snake_case_body_with_422(client) -> None:
    """異常系: リクエストボディが snake_case（`case_code`）だと 422（reviewer 指摘
    軽-1: 05-api-ipo.md 0.4 の camelCase 契約を入力側でも守る）。"""
    response = client.post(CASES_PATH, json={"case_code": "CASE-SNAKE-001"})

    assert response.status_code == 422


def test_create_case_rejects_duplicate_case_code_with_409(client) -> None:
    """異常系: 同じ caseCode を2回作成すると2回目は 409 E_DUPLICATE_CASE_CODE。"""
    payload = {"caseCode": "CASE-DUP-001", "customerName": None, "title": None}
    first = client.post(CASES_PATH, json=payload)
    assert first.status_code == 201

    second = client.post(CASES_PATH, json=payload)

    assert second.status_code == 409
    body = second.json()
    assert body["code"] == "E_DUPLICATE_CASE_CODE"
    # 中-8: details のキーは camelCase（05-api-ipo.md 0.4）。snake_case
    # （case_code）で漏れていたのを reviewer が実応答で検出したため固定する。
    assert body["details"] == {"caseCode": "CASE-DUP-001"}


def test_list_cases_returns_intake_status_when_no_version_exists(client) -> None:
    """正常系: 版が無い案件の進捗ステータスは①資料投入（'intake'）。

    05-api-ipo.md 5章「①資料投入=案件があり確定版なし」に対応。
    ②案の確認以降（版がある場合）は versions の Repository ができてから
    テストを足す（T-201 以降・orchestrator 指示）。
    """
    create_resp = client.post(
        CASES_PATH,
        json={"caseCode": "CASE-LIST-001", "customerName": None, "title": None},
    )
    assert create_resp.status_code == 201
    case_id = create_resp.json()["caseId"]

    list_resp = client.get(CASES_PATH)

    assert list_resp.status_code == 200
    cases = list_resp.json()["cases"]
    target = next(c for c in cases if c["caseId"] == case_id)
    assert target["progressStatus"] == "intake"


def test_get_case_by_id_returns_200(client) -> None:
    """正常系: 存在する案件IDで基本情報が取得できる。"""
    create_resp = client.post(
        CASES_PATH,
        json={"caseCode": "CASE-GET-001", "customerName": "客先A", "title": "件名A"},
    )
    case_id = create_resp.json()["caseId"]

    response = client.get(f"{CASES_PATH}/{case_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["caseId"] == case_id
    assert body["caseCode"] == "CASE-GET-001"


def test_get_case_by_id_404_when_missing(client) -> None:
    """異常系: 存在しない案件IDは 404 E_NOT_FOUND。"""
    response = client.get(f"{CASES_PATH}/999999")

    assert response.status_code == 404
    assert response.json()["code"] == "E_NOT_FOUND"
