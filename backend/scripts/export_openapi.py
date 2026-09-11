"""FastAPI OpenAPI スキーマをエクスポートする。

frontend の orval が読む openapi.json を生成する（Slice 0-6）。
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Export OpenAPI schema")
    parser.add_argument("-o", "--output", default="openapi.json")
    args = parser.parse_args()

    schema = app.openapi()
    with open(args.output, "w") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)

    print(f"OpenAPI schema exported to: {args.output}")


if __name__ == "__main__":
    main()
