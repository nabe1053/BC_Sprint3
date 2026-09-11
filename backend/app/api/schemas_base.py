"""Presentation 層の DTO 共通基底。

05-api-ipo.md 0.4「JSON のフィールド名は camelCase。DB の列名（snake_case）を
そのまま外に出さない」。Pydantic モデルは snake_case の属性名で定義し、
`alias_generator=to_camel` で入出力だけを camelCase に変換する
（Python コード側は他の層と同じ命名規約のままにする）。
"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """snake_case 属性 ⇄ camelCase JSON の変換を行う基底モデル。

    `populate_by_name=True` はレスポンス DTO を Python 側で snake_case の
    キーワード引数から組み立てる（`CaseResponse(case_id=..., ...)` 等）ために
    必要（外すと応答の組み立てが軒並み壊れる）。**入力（リクエストボディ）の
    DTO は代わりに `CamelRequestModel` を使うこと**（reviewer 指摘 軽-1: 05-api-ipo.md
    0.4 の camelCase 契約は入力側でも守る＝snake_case 入力は 422 で拒否する）。
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class CamelRequestModel(CamelModel):
    """リクエストボディ専用の基底モデル。

    `populate_by_name=False` にして camelCase 以外（snake_case 等）のキーを
    拒否する（05-api-ipo.md 0.4・reviewer 指摘 軽-1）。リクエスト DTO は
    サーバ内部で Python kwargs から組み立てることが無い（常に HTTP ボディの
    JSON から `model_validate` される）ため、`populate_by_name=True` を維持する
    必要が無い。
    """

    # pydantic 2.11+ は `populate_by_name` を非推奨化し `validate_by_name` /
    # `validate_by_alias` に置き換えた。`populate_by_name=False` だけでは
    # 親（CamelModel）から継承した `validate_by_name=True` が残ってしまい
    # snake_case 入力が通ってしまうため、`validate_by_name` を明示的に False
    # にする（`validate_by_alias=True` で camelCase 入力は引き続き受理する）。
    model_config = ConfigDict(
        alias_generator=to_camel, validate_by_name=False, validate_by_alias=True
    )
