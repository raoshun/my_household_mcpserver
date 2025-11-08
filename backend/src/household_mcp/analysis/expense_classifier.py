"""
支出分類モジュール

IQR法と統計的手法を使用して、支出を定期的/不定期的に分類します。
"""

from __future__ import annotations

from statistics import mean, stdev
from typing import NamedTuple

import numpy as np


class ClassificationResult(NamedTuple):
    """支出分類結果"""

    classification: str  # "regular" or "irregular"
    confidence: float  # 0.0-1.0
    reasoning: dict  # 分類根拠の詳細情報


class ExpenseClassifier:
    """
    支出分類クラス

    IQR法（四分位数範囲）、発生頻度、変動係数を組み合わせて
    支出を定期的（regular）/不定期的（irregular）に分類します。
    """

    # 分類閾値
    IQR_THRESHOLD = 1.5  # IQRの倍率
    OCCURRENCE_RATE_THRESHOLD = 0.6  # 発生頻度の閾値（60%以上は定期的）
    CV_THRESHOLD = 0.3  # 変動係数の閾値（30%以下は定期的）

    @staticmethod
    def classify_by_iqr(amounts: list[float], threshold: float = IQR_THRESHOLD) -> dict:
        """
        IQR法による異常値判定と変動性分析

        Args:
            amounts: 支出額のリスト
            threshold: IQRの倍率

        Returns:
            分析結果辞書:
            - has_outliers: 異常値の有無
            - outlier_count: 異常値の個数
            - outlier_ratio: 異常値の割合
            - iqr: 四分位数範囲
            - q1, q3: 第1四分位数、第3四分位数

        """
        if len(amounts) < 4:
            return {
                "has_outliers": False,
                "outlier_count": 0,
                "outlier_ratio": 0.0,
                "iqr": 0.0,
                "q1": 0.0,
                "q3": 0.0,
            }

        q1 = np.percentile(amounts, 25)
        q3 = np.percentile(amounts, 75)
        iqr = q3 - q1

        lower_bound = q1 - threshold * iqr
        upper_bound = q3 + threshold * iqr

        outliers = [a for a in amounts if a < lower_bound or a > upper_bound]

        return {
            "has_outliers": len(outliers) > 0,
            "outlier_count": len(outliers),
            "outlier_ratio": len(outliers) / len(amounts),
            "iqr": float(iqr),
            "q1": float(q1),
            "q3": float(q3),
            "lower_bound": float(lower_bound),
            "upper_bound": float(upper_bound),
        }

    @staticmethod
    def classify_by_occurrence(
        months: int, occurrences: int, threshold: float = OCCURRENCE_RATE_THRESHOLD
    ) -> dict:
        """
        発生頻度による分類

        Args:
            months: 分析対象月数
            occurrences: 実際の発生月数
            threshold: 定期的と判定する頻度の閾値

        Returns:
            分析結果辞書:
            - occurrence_rate: 発生頻度（0.0-1.0）
            - is_regular: 定期的かどうか
            - interpretation: 解釈テキスト

        """
        if months <= 0:
            raise ValueError(f"月数は正の数である必要があります: {months}")

        occurrence_rate = occurrences / months

        return {
            "occurrence_rate": round(occurrence_rate, 3),
            "is_regular": occurrence_rate >= threshold,
            "occurrences": occurrences,
            "months": months,
            "interpretation": (
                f"対象{months}ヶ月中{occurrences}ヶ月に発生（{occurrence_rate * 100:.1f}%）"
            ),
        }

    @staticmethod
    def classify_by_cv(amounts: list[float], threshold: float = CV_THRESHOLD) -> dict:
        """
        変動係数（Coefficient of Variation）による分類

        Args:
            amounts: 支出額のリスト（0以外の発生した月のみ）
            threshold: 変動係数の閾値

        Returns:
            分析結果辞書:
            - cv: 変動係数（0.0-1.0+）
            - is_stable: 安定的かどうか
            - mean: 平均値
            - std: 標準偏差

        """
        if len(amounts) < 2:
            return {
                "cv": 0.0,
                "is_stable": True,
                "mean": float(amounts[0]) if amounts else 0.0,
                "std": 0.0,
                "interpretation": "データポイント数が不足",
            }

        mean_val = mean(amounts)

        if mean_val == 0:
            raise ValueError("平均値が0のため変動係数を計算できません")

        std_val = stdev(amounts)
        cv = std_val / abs(mean_val)

        return {
            "cv": round(cv, 3),
            "is_stable": cv <= threshold,
            "mean": round(mean_val, 2),
            "std": round(std_val, 2),
            "interpretation": (
                f"変動係数: {cv:.3f} ({'安定' if cv <= threshold else '変動'})"
            ),
        }

    @staticmethod
    def calculate_confidence(
        iqr_result: dict, occurrence_result: dict, cv_result: dict
    ) -> float:
        """
        3つの指標から総合的な信頼度を計算（0.0-1.0）

        スコアリング：
        - IQR異常値少なし: +0.3
        - 発生頻度高い: +0.35
        - 変動係数低い: +0.35

        Args:
            iqr_result: classify_by_irrの結果
            occurrence_result: classify_by_occurrenceの結果
            cv_result: classify_by_cvの結果

        Returns:
            信頼度（0.0-1.0）

        """
        confidence = 0.0

        # IQR スコア
        if not iqr_result.get("has_outliers", True):
            confidence += 0.3
        else:
            # 異常値割合が少ない場合は部分的にスコア
            outlier_ratio = iqr_result.get("outlier_ratio", 1.0)
            confidence += max(0, 0.3 * (1 - outlier_ratio))

        # 発生頻度 スコア
        if occurrence_result.get("is_regular", False):
            confidence += 0.35
        else:
            occurrence_rate = occurrence_result.get("occurrence_rate", 0.0)
            confidence += max(0, 0.35 * occurrence_rate)

        # 変動係数 スコア
        if cv_result.get("is_stable", False):
            confidence += 0.35
        else:
            cv = cv_result.get("cv", 1.0)
            # CV が大きいほど信頼度は低下
            confidence += max(0, 0.35 * max(0, 1 - cv))

        return round(min(1.0, confidence), 3)

    @classmethod
    def classify(
        cls,
        amounts: list[float],
        months: int,
        occurrences: int,
        use_default_thresholds: bool = True,
    ) -> ClassificationResult:
        """
        総合的な支出分類を実行

        Args:
            amounts: 発生した月の支出額リスト
            months: 分析対象月数
            occurrences: 実際の発生月数
            use_default_thresholds: デフォルト閾値を使用するか

        Returns:
            ClassificationResult: 分類結果（classification, confidence, reasoning）

        """
        if len(amounts) != occurrences:
            raise ValueError(
                f"amountsの長さ({len(amounts)})とoccurrences({occurrences})が一致しません"
            )

        if occurrences == 0:
            return ClassificationResult(
                classification="irregular",
                confidence=1.0,
                reasoning={"reason": "発生なし", "iqr": {}, "occurrence": {}, "cv": {}},
            )

        # 3つの指標を計算
        iqr_result = cls.classify_by_iqr(amounts)
        occurrence_result = cls.classify_by_occurrence(months, occurrences)
        cv_result = cls.classify_by_cv(amounts)

        # 信頼度を計算
        confidence = cls.calculate_confidence(iqr_result, occurrence_result, cv_result)

        # 分類ロジック：
        # - 発生頻度 >= 60% かつ 変動係数 <= 30% → 定期的
        # - その他 → 不定期的
        is_regular = occurrence_result.get("is_regular", False) and cv_result.get(
            "is_stable", False
        )

        classification = "regular" if is_regular else "irregular"

        return ClassificationResult(
            classification=classification,
            confidence=confidence,
            reasoning={
                "iqr": iqr_result,
                "occurrence": occurrence_result,
                "cv": cv_result,
            },
        )
