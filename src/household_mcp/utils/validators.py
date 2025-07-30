"""データバリデーション機能.

家計簿データの妥当性検証とエラーチェック機能を提供
"""

import re
from datetime import date as date_type
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Union


class ValidationError(Exception):
    """バリデーションエラー."""

    def __init__(self, message: str, field: Optional[str] = None):
        """初期化.

        Args:
            message: エラーメッセージ
            field: エラーが発生したフィールド名
        """
        self.message = message
        self.field = field
        super().__init__(self.message)


class DataValidator:
    """データバリデーター."""

    # 日付フォーマットパターン
    DATE_PATTERNS = [
        r"^\d{4}-\d{2}-\d{2}$",  # YYYY-MM-DD
        r"^\d{4}/\d{2}/\d{2}$",  # YYYY/MM/DD
        r"^\d{2}/\d{2}/\d{4}$",  # MM/DD/YYYY
        r"^\d{2}-\d{2}-\d{4}$",  # MM-DD-YYYY
    ]

    # 金額の最大値・最小値
    MIN_AMOUNT = Decimal("-999999999.99")
    MAX_AMOUNT = Decimal("999999999.99")

    @classmethod
    def validate_date(
        cls, date_str: Union[str, datetime, date_type], field_name: str = "date"
    ) -> date_type:
        """日付の妥当性を検証.

        Args:
            date_str: 日付文字列またはdatetimeオブジェクト
            field_name: フィールド名

        Returns:
            検証済みの日付オブジェクト

        Raises:
            ValidationError: 日付が無効な場合
        """
        if date_str is None:
            raise ValidationError(f"{field_name}は必須です", field_name)

        # 既にdateオブジェクトの場合
        if isinstance(date_str, date_type):
            return date_str

        # datetimeオブジェクトの場合
        if isinstance(date_str, datetime):
            return date_str.date()

        # 文字列の場合
        if not isinstance(date_str, str):
            raise ValidationError(
                f"{field_name}は文字列である必要があります", field_name
            )

        date_str = date_str.strip()
        if not date_str:
            raise ValidationError(f"{field_name}は必須です", field_name)

        # パターンマッチング
        valid_format = False
        for pattern in cls.DATE_PATTERNS:
            if re.match(pattern, date_str):
                valid_format = True
                break

        if not valid_format:
            raise ValidationError(
                f"{field_name}の形式が正しくありません。YYYY-MM-DD形式で入力してください",
                field_name,
            )

        # 実際の日付として解析
        try:
            # 様々な区切り文字を統一
            normalized = date_str.replace("/", "-")

            # MM-DD-YYYY形式の場合は変換
            if re.match(r"^\d{2}-\d{2}-\d{4}$", normalized):
                parts = normalized.split("-")
                normalized = f"{parts[2]}-{parts[0]}-{parts[1]}"

            parsed_date = datetime.strptime(normalized, "%Y-%m-%d").date()

            # 現在より未来すぎる日付をチェック
            today = datetime.now().date()
            if parsed_date > today:
                # 1年以上未来の場合は警告
                from datetime import timedelta

                if parsed_date > today + timedelta(days=365):
                    raise ValidationError(
                        f"{field_name}が未来すぎます: {parsed_date}", field_name
                    )

            # 過去すぎる日付をチェック（100年前まで）
            min_date = datetime(today.year - 100, 1, 1).date()
            if parsed_date < min_date:
                raise ValidationError(
                    f"{field_name}が古すぎます: {parsed_date}", field_name
                )

            return parsed_date

        except ValueError as e:
            raise ValidationError(
                f"{field_name}の日付が無効です: {date_str}", field_name
            ) from e

    @classmethod
    def validate_amount(
        cls, amount: Union[str, int, float, Decimal], field_name: str = "amount"
    ) -> Decimal:
        """金額の妥当性を検証.

        Args:
            amount: 金額
            field_name: フィールド名

        Returns:
            検証済みの金額

        Raises:
            ValidationError: 金額が無効な場合
        """
        if amount is None:
            raise ValidationError(f"{field_name}は必須です", field_name)

        # 既にDecimalの場合
        if isinstance(amount, Decimal):
            validated_amount = amount
        else:
            # 文字列の場合は前処理
            if isinstance(amount, str):
                amount = amount.strip()
                if not amount:
                    raise ValidationError(f"{field_name}は必須です", field_name)

                # カンマや円マークを除去
                amount = amount.replace(",", "").replace("￥", "").replace("¥", "")

                # 全角数字を半角に変換
                amount = amount.translate(
                    str.maketrans("０１２３４５６７８９", "0123456789")
                )

            # Decimalに変換
            try:
                validated_amount = Decimal(str(amount))
            except (InvalidOperation, ValueError) as e:
                raise ValidationError(
                    f"{field_name}は有効な数値である必要があります: {amount}",
                    field_name,
                ) from e

        # 範囲チェック
        if validated_amount < cls.MIN_AMOUNT:
            raise ValidationError(
                f"{field_name}が最小値を下回っています: {validated_amount}", field_name
            )

        if validated_amount > cls.MAX_AMOUNT:
            raise ValidationError(
                f"{field_name}が最大値を超えています: {validated_amount}", field_name
            )

        # 小数点以下桁数チェック（2桁まで）
        decimal_tuple = validated_amount.as_tuple()
        if decimal_tuple.exponent == "n" or decimal_tuple.exponent == "N":
            # NaN or infinity
            raise ValidationError(
                f"{field_name}は有効な数値である必要があります: {validated_amount}",
                field_name,
            )
        elif isinstance(decimal_tuple.exponent, int) and decimal_tuple.exponent < -2:
            raise ValidationError(
                f"{field_name}の小数点以下は2桁までです: {validated_amount}", field_name
            )

        return validated_amount

    @classmethod
    def validate_string(
        cls,
        value: Any,
        field_name: str,
        required: bool = True,
        min_length: int = 0,
        max_length: int = 255,
        pattern: Optional[str] = None,
    ) -> Optional[str]:
        """文字列の妥当性を検証.

        Args:
            value: 検証する値
            field_name: フィールド名
            required: 必須フィールドかどうか
            min_length: 最小文字数
            max_length: 最大文字数
            pattern: 正規表現パターン

        Returns:
            検証済みの文字列

        Raises:
            ValidationError: 文字列が無効な場合
        """
        if value is None:
            if required:
                raise ValidationError(f"{field_name}は必須です", field_name)
            return None

        if not isinstance(value, str):
            value = str(value)

        value = value.strip()

        if required and not value:
            raise ValidationError(f"{field_name}は必須です", field_name)

        if len(value) < min_length:
            raise ValidationError(
                f"{field_name}は{min_length}文字以上である必要があります", field_name
            )

        if len(value) > max_length:
            raise ValidationError(
                f"{field_name}は{max_length}文字以下である必要があります", field_name
            )

        if pattern and not re.match(pattern, value):
            raise ValidationError(f"{field_name}の形式が正しくありません", field_name)

        return value if value else None

    @classmethod
    def validate_enum(
        cls,
        value: Any,
        field_name: str,
        allowed_values: List[str],
        required: bool = True,
    ) -> Optional[str]:
        """列挙値の妥当性を検証.

        Args:
            value: 検証する値
            field_name: フィールド名
            allowed_values: 許可された値のリスト
            required: 必須フィールドかどうか

        Returns:
            検証済みの値

        Raises:
            ValidationError: 値が無効な場合
        """
        if value is None:
            if required:
                raise ValidationError(f"{field_name}は必須です", field_name)
            return None

        if not isinstance(value, str):
            value = str(value)

        value = value.strip().lower()

        # 大文字小文字を無視して比較
        allowed_lower = [v.lower() for v in allowed_values]

        if value not in allowed_lower:
            raise ValidationError(
                f"{field_name}は次のいずれかである必要があります: {', '.join(allowed_values)}",
                field_name,
            )

        # 元の形式を返す
        return allowed_values[allowed_lower.index(value)]

    @classmethod
    def validate_transaction_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """取引データ全体の妥当性を検証.

        Args:
            data: 取引データ

        Returns:
            検証済みの取引データ

        Raises:
            ValidationError: データが無効な場合
        """
        validated = {}

        # 日付の検証
        validated["date"] = cls.validate_date(data.get("date"), "date")

        # 金額の検証
        validated["amount"] = cls.validate_amount(data.get("amount"), "amount")

        # 説明の検証
        validated["description"] = cls.validate_string(
            data.get("description"),
            "description",
            required=True,
            min_length=1,
            max_length=500,
        )

        # 種別の検証
        validated["type"] = cls.validate_enum(
            data.get("type"), "type", ["income", "expense"], required=True
        )

        # カテゴリー名の検証（オプション）
        if "category_name" in data:
            validated["category_name"] = cls.validate_string(
                data.get("category_name"),
                "category_name",
                required=False,
                max_length=100,
            )

        # アカウント名の検証（オプション）
        if "account_name" in data:
            validated["account_name"] = cls.validate_string(
                data.get("account_name"), "account_name", required=False, max_length=100
            )

        return validated

    @classmethod
    def validate_category_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """カテゴリーデータの妥当性を検証.

        Args:
            data: カテゴリーデータ

        Returns:
            検証済みのカテゴリーデータ

        Raises:
            ValidationError: データが無効な場合
        """
        validated = {}

        # 名前の検証
        validated["name"] = cls.validate_string(
            data.get("name"), "name", required=True, min_length=1, max_length=100
        )

        # 種別の検証
        validated["type"] = cls.validate_enum(
            data.get("type"), "type", ["income", "expense"], required=True
        )

        # 色の検証（オプション）
        if "color" in data:
            validated["color"] = cls.validate_string(
                data.get("color"), "color", required=False, pattern=r"^#[0-9a-fA-F]{6}$"
            )

        # アイコンの検証（オプション）
        if "icon" in data:
            validated["icon"] = cls.validate_string(
                data.get("icon"), "icon", required=False, max_length=50
            )

        return validated

    @classmethod
    def validate_account_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """アカウントデータの妥当性を検証.

        Args:
            data: アカウントデータ

        Returns:
            検証済みのアカウントデータ

        Raises:
            ValidationError: データが無効な場合
        """
        validated = {}

        # 名前の検証
        validated["name"] = cls.validate_string(
            data.get("name"), "name", required=True, min_length=1, max_length=100
        )

        # 種別の検証
        validated["type"] = cls.validate_enum(
            data.get("type"),
            "type",
            ["bank", "cash", "credit", "investment"],
            required=True,
        )

        # 初期残高の検証（オプション）
        if "initial_balance" in data:
            validated["initial_balance"] = cls.validate_amount(
                data.get("initial_balance", 0), "initial_balance"
            )

        return validated


def validate_bulk_data(
    data_list: List[Dict[str, Any]], data_type: str
) -> Dict[str, Any]:
    """一括データの妥当性を検証.

    Args:
        data_list: データのリスト
        data_type: データ種別 ('transaction', 'category', 'account')

    Returns:
        検証結果
    """
    results = {"valid_count": 0, "error_count": 0, "errors": [], "validated_data": []}

    validator_map = {
        "transaction": DataValidator.validate_transaction_data,
        "category": DataValidator.validate_category_data,
        "account": DataValidator.validate_account_data,
    }

    validator = validator_map.get(data_type)
    if not validator:
        raise ValueError(f"不明なデータ種別: {data_type}")

    for i, item in enumerate(data_list):
        try:
            validated = validator(item)
            results["validated_data"].append(validated)
            results["valid_count"] += 1
        except ValidationError as e:
            results["error_count"] += 1
            results["errors"].append(
                {"row": i + 1, "field": e.field, "message": e.message, "data": item}
            )
        except Exception as e:
            results["error_count"] += 1
            results["errors"].append(
                {"row": i + 1, "field": None, "message": str(e), "data": item}
            )

    return results
