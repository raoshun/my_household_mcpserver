"""
FIRE (Financial Independence, Retire Early) 計算モジュール

FIRE基準に基づいた目標資産額の計算と関連ユーティリティを提供します。
"""

from __future__ import annotations


class FIRECalculator:
    """FIRE基準に基づいて目標資産額を計算するクラス"""

    # FIRE基準: 年支出額 × 25
    FIRE_MULTIPLIER = 25

    @staticmethod
    def calculate_fire_target(
        annual_expense: float, custom_multiplier: float | None = None
    ) -> float:
        """
        FIRE基準に基づいて目標資産額を計算

        Args:
            annual_expense: 年支出額（円）
            custom_multiplier: カスタム倍率（デフォルト: 25）

        Returns:
            目標資産額（円）

        Raises:
            ValueError: 年支出額が0以下の場合

        """
        if annual_expense <= 0:
            raise ValueError(f"年支出額は正の数である必要があります: {annual_expense}")

        if custom_multiplier is not None:
            if custom_multiplier <= 0:
                raise ValueError(
                    f"倍率は正の数である必要があります: {custom_multiplier}"
                )
            multiplier = custom_multiplier
        else:
            multiplier = FIRECalculator.FIRE_MULTIPLIER

        return annual_expense * multiplier

    @staticmethod
    def calculate_progress_rate(current_assets: float, target_assets: float) -> float:
        """
        FIRE目標への進捗率を計算（%）

        Args:
            current_assets: 現在の純資産（円）
            target_assets: 目標資産額（円）

        Returns:
            進捗率（0〜100%、目標達成時は100以上の値も可能）

        """
        if target_assets <= 0:
            raise ValueError(f"目標資産額は正の数である必要があります: {target_assets}")

        progress_rate = (current_assets / target_assets) * 100
        return round(progress_rate, 2)

    @staticmethod
    def is_fi_achieved(current_assets: float, target_assets: float) -> bool:
        """
        経済的自由に達成したかどうかを判定

        Args:
            current_assets: 現在の純資産（円）
            target_assets: 目標資産額（円）

        Returns:
            True: 達成済み、False: 未達成

        """
        return current_assets >= target_assets
