"""データフォーマッター機能.

家計簿データの表示形式を統一するフォーマット機能を提供
"""

from datetime import date as date_type
from datetime import datetime
from decimal import Decimal
from typing import Union


class DataFormatter:
    """データフォーマッター."""

    @staticmethod
    def format_currency(
        amount: Union[int, float, Decimal, str],
        currency_code: str = "JPY",
        include_symbol: bool = True,
        use_grouping: bool = True,
    ) -> str:
        """通貨フォーマット.

        Args:
            amount: 金額
            currency_code: 通貨コード
            include_symbol: 通貨記号を含めるか
            use_grouping: 3桁区切りを使用するか

        Returns:
            フォーマット済み通貨文字列
        """
        try:
            # Decimalに変換
            if isinstance(amount, str):
                decimal_amount = Decimal(amount.replace(",", ""))
            else:
                decimal_amount = Decimal(str(amount))

            # 整数として表示するか小数として表示するかを判断
            if decimal_amount % 1 == 0:
                # 整数の場合
                formatted = (
                    f"{int(decimal_amount):,}"
                    if use_grouping
                    else str(int(decimal_amount))
                )
            else:
                # 小数の場合
                if use_grouping:
                    formatted = f"{float(decimal_amount):,.2f}"
                else:
                    formatted = f"{float(decimal_amount):.2f}"

            # 通貨記号の追加
            if include_symbol:
                if currency_code == "JPY":
                    return f"¥{formatted}"
                elif currency_code == "USD":
                    return f"${formatted}"
                elif currency_code == "EUR":
                    return f"€{formatted}"
                else:
                    return f"{formatted} {currency_code}"

            return formatted

        except (ValueError, TypeError):
            return str(amount)

    @staticmethod
    def format_date(
        date_obj: Union[datetime, date_type, str], format_type: str = "default"
    ) -> str:
        """日付フォーマット.

        Args:
            date_obj: 日付オブジェクトまたは文字列
            format_type: フォーマット種別
                - "default": YYYY年MM月DD日
                - "short": YYYY/MM/DD
                - "iso": YYYY-MM-DD
                - "jp": M月D日
                - "jp_year": YYYY年M月D日

        Returns:
            フォーマット済み日付文字列
        """
        try:
            # 文字列の場合は解析
            if isinstance(date_obj, str):
                # ISO形式を想定
                if "T" in date_obj:
                    date_obj = datetime.fromisoformat(
                        date_obj.replace("Z", "+00:00")
                    ).date()
                else:
                    date_obj = datetime.strptime(date_obj, "%Y-%m-%d").date()
            elif isinstance(date_obj, datetime):
                date_obj = date_obj.date()

            if format_type == "default":
                return f"{date_obj.year}年{date_obj.month:02d}月{date_obj.day:02d}日"
            elif format_type == "short":
                return date_obj.strftime("%Y/%m/%d")
            elif format_type == "iso":
                return date_obj.strftime("%Y-%m-%d")
            elif format_type == "jp":
                return f"{date_obj.month}月{date_obj.day}日"
            elif format_type == "jp_year":
                return f"{date_obj.year}年{date_obj.month}月{date_obj.day}日"
            else:
                return str(date_obj)

        except (ValueError, TypeError):
            return str(date_obj)

    @staticmethod
    def format_number(
        number: Union[int, float, Decimal, str],
        decimal_places: int = 2,
        use_grouping: bool = True,
        show_plus_sign: bool = False,
    ) -> str:
        """数値フォーマット.

        Args:
            number: 数値
            decimal_places: 小数点以下桁数
            use_grouping: 3桁区切りを使用するか
            show_plus_sign: 正の数に+記号を表示するか

        Returns:
            フォーマット済み数値文字列
        """
        try:
            # Decimalに変換
            if isinstance(number, str):
                decimal_number = Decimal(number.replace(",", ""))
            else:
                decimal_number = Decimal(str(number))

            # フォーマット文字列を構築
            if decimal_places == 0:
                if use_grouping:
                    formatted = f"{int(decimal_number):,}"
                else:
                    formatted = str(int(decimal_number))
            else:
                if use_grouping:
                    formatted = f"{float(decimal_number):,.{decimal_places}f}"
                else:
                    formatted = f"{float(decimal_number):.{decimal_places}f}"

            # +記号の追加
            if show_plus_sign and decimal_number > 0:
                formatted = f"+{formatted}"

            return formatted

        except (ValueError, TypeError):
            return str(number)

    @staticmethod
    def format_percentage(
        value: Union[int, float, Decimal, str],
        decimal_places: int = 1,
        multiply_by_100: bool = True,
    ) -> str:
        """パーセンテージフォーマット.

        Args:
            value: 値
            decimal_places: 小数点以下桁数
            multiply_by_100: 100倍するか（0.1 -> 10%）

        Returns:
            フォーマット済みパーセンテージ文字列
        """
        try:
            # Decimalに変換
            if isinstance(value, str):
                decimal_value = Decimal(value.replace("%", "").replace(",", ""))
            else:
                decimal_value = Decimal(str(value))

            # 100倍処理
            if multiply_by_100:
                decimal_value *= 100

            # フォーマット
            formatted = f"{float(decimal_value):.{decimal_places}f}%"

            return formatted

        except (ValueError, TypeError):
            return str(value)

    @staticmethod
    def format_transaction_type(transaction_type: str) -> str:
        """取引種別フォーマット.

        Args:
            transaction_type: 取引種別

        Returns:
            フォーマット済み取引種別
        """
        type_map = {
            "income": "収入",
            "expense": "支出",
            "transfer": "振替",
        }

        return type_map.get(transaction_type.lower(), transaction_type)

    @staticmethod
    def format_account_type(account_type: str) -> str:
        """アカウント種別フォーマット.

        Args:
            account_type: アカウント種別

        Returns:
            フォーマット済みアカウント種別
        """
        type_map = {
            "bank": "銀行口座",
            "cash": "現金",
            "credit": "クレジットカード",
            "investment": "投資口座",
            "savings": "貯蓄口座",
        }

        return type_map.get(account_type.lower(), account_type)

    @staticmethod
    def format_category_type(category_type: str) -> str:
        """カテゴリー種別フォーマット.

        Args:
            category_type: カテゴリー種別

        Returns:
            フォーマット済みカテゴリー種別
        """
        type_map = {
            "income": "収入カテゴリー",
            "expense": "支出カテゴリー",
        }

        return type_map.get(category_type.lower(), category_type)

    @staticmethod
    def format_boolean(
        value: bool, true_text: str = "はい", false_text: str = "いいえ"
    ) -> str:
        """真偽値フォーマット.

        Args:
            value: 真偽値
            true_text: Trueの場合のテキスト
            false_text: Falseの場合のテキスト

        Returns:
            フォーマット済み真偽値文字列
        """
        return true_text if value else false_text

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """ファイルサイズフォーマット.

        Args:
            size_bytes: バイト数

        Returns:
            フォーマット済みファイルサイズ
        """
        try:
            if size_bytes == 0:
                return "0 B"

            units = ["B", "KB", "MB", "GB", "TB"]
            unit_index = 0
            size = float(size_bytes)

            while size >= 1024 and unit_index < len(units) - 1:
                size /= 1024
                unit_index += 1

            if unit_index == 0:
                return f"{int(size)} {units[unit_index]}"
            else:
                return f"{size:.1f} {units[unit_index]}"

        except (ValueError, TypeError):
            return str(size_bytes)

    @classmethod
    def format_transaction_summary(cls, transaction: dict) -> dict:
        """取引データの表示用フォーマット.

        Args:
            transaction: 取引データ

        Returns:
            フォーマット済み取引データ
        """
        formatted = transaction.copy()

        # 日付のフォーマット
        if "date" in formatted:
            formatted["formatted_date"] = cls.format_date(formatted["date"])

        # 金額のフォーマット
        if "amount" in formatted:
            formatted["formatted_amount"] = cls.format_currency(formatted["amount"])

        # 取引種別のフォーマット
        if "type" in formatted:
            formatted["formatted_type"] = cls.format_transaction_type(formatted["type"])

        return formatted

    @classmethod
    def format_account_summary(cls, account: dict) -> dict:
        """アカウントデータの表示用フォーマット.

        Args:
            account: アカウントデータ

        Returns:
            フォーマット済みアカウントデータ
        """
        formatted = account.copy()

        # 残高のフォーマット
        if "current_balance" in formatted:
            formatted["formatted_balance"] = cls.format_currency(
                formatted["current_balance"]
            )

        if "initial_balance" in formatted:
            formatted["formatted_initial_balance"] = cls.format_currency(
                formatted["initial_balance"]
            )

        # アカウント種別のフォーマット
        if "type" in formatted:
            formatted["formatted_type"] = cls.format_account_type(formatted["type"])

        # アクティブ状態のフォーマット
        if "is_active" in formatted:
            formatted["formatted_active"] = cls.format_boolean(
                formatted["is_active"], "有効", "無効"
            )

        return formatted

    @classmethod
    def format_category_summary(cls, category: dict) -> dict:
        """カテゴリーデータの表示用フォーマット.

        Args:
            category: カテゴリーデータ

        Returns:
            フォーマット済みカテゴリーデータ
        """
        formatted = category.copy()

        # カテゴリー種別のフォーマット
        if "type" in formatted:
            formatted["formatted_type"] = cls.format_category_type(formatted["type"])

        return formatted


# 便利関数
def currency(amount: Union[int, float, Decimal, str], **kwargs) -> str:
    """通貨フォーマットのショートカット."""
    return DataFormatter.format_currency(amount, **kwargs)


def date_format(
    date_obj: Union[datetime, date_type, str], format_type: str = "default"
) -> str:
    """日付フォーマットのショートカット."""
    return DataFormatter.format_date(date_obj, format_type)


def number(value: Union[int, float, Decimal, str], **kwargs) -> str:
    """数値フォーマットのショートカット."""
    return DataFormatter.format_number(value, **kwargs)


def percentage(value: Union[int, float, Decimal, str], **kwargs) -> str:
    """パーセンテージフォーマットのショートカット."""
    return DataFormatter.format_percentage(value, **kwargs)
