"""Required human-record routes must exist under UI only."""


def test_all_version_and_record_routes_exist_under_ui():
    from app.main import app

    paths = {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", [])
    }
    expected = {
        ("POST", "/versions/{versionId}/exports"),
        ("GET", "/versions/{versionId}/exports"),
        ("GET", "/versions/{versionId}/evidence"),
        ("GET", "/versions/{versionId}/records"),
        ("POST", "/versions/{versionId}/state-events"),
        ("POST", "/versions/{versionId}/bounce-comments"),
        ("POST", "/versions/{versionId}/bounces"),
        ("POST", "/versions/{versionId}/sendoff-decisions"),
        ("GET", "/cases/{caseId}/versions"),
        ("GET", "/versions/{versionId}"),
        ("GET", "/versions/{versionId}/items"),
        ("GET", "/versions/{versionId}/items/{itemId}/evidence"),
        ("GET", "/versions/{versionId}/questions"),
        ("GET", "/versions/{versionId}/inventory"),
        ("POST", "/versions/{versionId}/edits"),
        ("POST", "/versions/{versionId}/edits/{editId}/undo"),
        ("POST", "/versions/{versionId}/confirmations"),
        ("POST", "/versions/{versionId}/confirmations/{confirmationId}/undo"),
        ("POST", "/versions/{versionId}/questions/{questionId}/judgements"),
    }
    assert {(method, "/api/v1/ui" + path) for method, path in expected} <= paths


def test_inventory_path_is_method_split_between_agent_and_ui():
    from app.main import app

    paths = {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", [])
    }
    assert ("GET", "/api/v1/agent/versions/{versionId}/inventory") not in paths
    assert ("POST", "/api/v1/ui/versions/{versionId}/inventory") not in paths
    assert ("POST", "/api/v1/agent/versions/{versionId}/inventory") in paths


def test_bulk_evidence_and_exports_preserve_method_boundary():
    from app.main import app

    paths = {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", [])
    }
    assert ("POST", "/api/v1/agent/versions/{versionId}/evidence") in paths
    assert ("GET", "/api/v1/agent/versions/{versionId}/evidence") not in paths
    assert ("POST", "/api/v1/ui/versions/{versionId}/evidence") not in paths
    assert not any(path.endswith("/exports") and "/agent/" in path for _, path in paths)
    assert ("GET", "/api/v1/ui/versions/{versionId}/evidence") in paths
