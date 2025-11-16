"""RealEstateCashflowAnalyzer 最適化版単体テスト

TASK-2004: Phase 1 単体テスト
"""

from datetime import date
from decimal import Decimal
from unittest.mock import Mock, mock_open, patch

import pandas as pd
import pytest

from household_mcp.analysis.income_analyzer import IncomeAnalyzer
from household_mcp.analysis.real_estate_cashflow_analyzer import (
    RealEstateCashflow,
    RealEstateCashflowAnalyzer,
)
from household_mcp.dataloader import HouseholdDataLoader


@pytest.fixture
def property_database_json():
    """サンプル物件データベースJSON"""
    return """{
        "property_001": {
            "name": "マンションA号室",
            "initial_investment": 30000000,
            "purchase_date": "2020-04-01"
        },
        "property_002": {
            "name": "駐車場B",
            "initial_investment": 5000000,
            "purchase_date": "2021-01-15"
        }
    }"""


@pytest.fixture
def mock_data_loader():
    """モックデータローダー"""
    return Mock(spec=HouseholdDataLoader)


@pytest.fixture
def mock_income_analyzer():
    """モックIncomeAnalyzer"""
    return Mock(spec=IncomeAnalyzer)


@pytest.fixture
def analyzer(mock_income_analyzer, mock_data_loader, property_database_json):
    """RealEstateCashflowAnalyzer インスタンス"""
    with patch("builtins.open", mock_open(read_data=property_database_json)):
        return RealEstateCashflowAnalyzer(mock_income_analyzer, mock_data_loader)


class TestRealEstateCashflow:
    """不動産キャッシュフロー計算テスト"""

    def test_positive_cashflow(self, analyzer, mock_data_loader):
        """黒字キャッシュフロー"""
        data = pd.DataFrame(
            {
                "日付": pd.to_datetime(["2024-07-05", "2024-07-10"]),
                "金額（円）": [100000, -20000],
                "計算対象": [1, 1],
                "大項目": ["不動産", "住宅"],
                "中項目": ["家賃収入", "管理費"],
                "備考": ["property_001", "property_001"],
            }
        )
        mock_data_loader.load.return_value = data

        cashflow = analyzer.calculate_cashflow(
            date(2024, 7, 1), date(2024, 7, 31), "property_001"
        )

        assert cashflow.income == Decimal("100000.00")
        assert cashflow.expense == Decimal("20000.00")
        assert cashflow.net_cashflow == Decimal("80000.00")

    def test_roi_calculation(self, analyzer, mock_data_loader):
        """ROI計算（年間データ）"""
        # _load_period_data()をモックして年間データ（12ヶ月分）を返す
        annual_data = pd.DataFrame(
            {
                "日付": pd.to_datetime(
                    [f"2024-{m:02d}-05" for m in range(1, 13)]
                    + [f"2024-{m:02d}-10" for m in range(1, 13)]
                ),
                "金額（円）": [100000] * 12 + [-30000] * 12,
                "計算対象": [1] * 24,
                "大項目": ["不動産"] * 12 + ["住宅"] * 12,
                "中項目": ["家賃収入"] * 12 + ["管理費"] * 12,
                "備考": ["property_001"] * 24,
            }
        )

        with patch.object(analyzer, "_load_period_data", return_value=annual_data):
            cashflow = analyzer.calculate_cashflow(
                date(2024, 1, 1), date(2024, 12, 31), "property_001"
            )

        # 年間キャッシュフロー: 70000 * 12 = 840000
        # ROI: (840000 / 30000000) * 100 = 2.8%
        assert cashflow.net_cashflow == Decimal("840000.00")
        expected_roi = Decimal("2.80")
        assert cashflow.roi is not None
        assert abs(cashflow.roi - expected_roi) < Decimal("0.01")


class TestPropertyDatabase:
    """物件データベーステスト"""

    def test_load_property_database(
        self, mock_income_analyzer, mock_data_loader, property_database_json
    ):
        """物件データベース読み込み"""
        with patch("builtins.open", mock_open(read_data=property_database_json)):
            analyzer = RealEstateCashflowAnalyzer(
                mock_income_analyzer, mock_data_loader
            )

            assert "property_001" in analyzer.property_db
            assert (
                analyzer.property_db["property_001"]["initial_investment"] == 30000000
            )


class TestRealEstateCashflowDataclass:
    """RealEstateCashflowデータクラステスト"""

    def test_to_dict_conversion(self):
        """辞書変換が正しく動作する"""
        cashflow = RealEstateCashflow(
            property_id="property_001",
            year=2024,
            month=7,
            income=Decimal("100000.00"),
            expense=Decimal("30000.00"),
            net_cashflow=Decimal("70000.00"),
            roi=Decimal("2.80"),
        )

        result = cashflow.to_dict()

        assert result["property_id"] == "property_001"
        assert result["year"] == 2024
        assert result["income"] == 100000.0
        assert isinstance(result["roi"], float)
