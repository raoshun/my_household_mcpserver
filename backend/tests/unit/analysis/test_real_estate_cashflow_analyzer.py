"""RealEstateCashflowAnalyzer 単体テスト

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
def mock_data_loader():
    """モックデータローダー"""
    loader = Mock(spec=HouseholdDataLoader)
    return loader


@pytest.fixture
def mock_income_analyzer():
    """モックIncomeAnalyzer"""
    analyzer = Mock(spec=IncomeAnalyzer)
    return analyzer


@pytest.fixture
def sample_real_estate_data():
    """サンプル不動産関連データ"""
    return pd.DataFrame(
        {
            "日付": pd.to_datetime(
                [
                    "2024-07-05",
                    "2024-07-10",
                    "2024-07-15",
                    "2024-07-20",
                    "2024-07-25",
                ]
            ),
            "金額（円）": [100000, -20000, -10000, 50000, -5000],
            "計算対象": [1, 1, 1, 1, 1],
            "大項目": ["不動産", "住宅", "住宅", "不動産", "不動産"],
            "中項目": ["家賃収入", "管理費", "修繕費", "駐車場収入", "固定資産税"],
            "備考": [
                "property_001",
                "property_001",
                "property_001",
                "property_002",
                "property_002",
            ],
        }
    )


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
def analyzer(mock_income_analyzer, mock_data_loader, property_database_json):
    """RealEstateCashflowAnalyzer インスタンス"""
    with patch(
        "builtins.open", mock_open(read_data=property_database_json)
    ):
        return RealEstateCashflowAnalyzer(mock_income_analyzer, mock_data_loader)


class TestRealEstateIncomeExtraction:
    """不動産収入抽出テスト"""

    def test_extract_income_with_keywords(
        self, analyzer, mock_data_loader, sample_real_estate_data
    ):
        """不動産収入キーワードで正しく抽出"""
        mock_data_loader.load.return_value = sample_real_estate_data

        cashflow = analyzer.calculate_cashflow(
            date(2024, 7, 1), date(2024, 7, 31), "property_001"
        )

        # property_001の収入: 100000（家賃収入）
        assert cashflow.income == Decimal("100000.00")

    def test_extract_positive_amounts_only(
        self, analyzer, mock_data_loader, sample_real_estate_data
    ):
        """正の金額のみを収入として抽出"""
        mock_data_loader.load.return_value = sample_real_estate_data

        cashflow = analyzer.calculate_cashflow(
            "property_001", date(2024, 7, 1), date(2024, 7, 31)
        )

        # 負の金額は収入に含まれない
        assert cashflow.income > 0

    def test_filter_by_property_id(
        self, analyzer, mock_data_loader, sample_real_estate_data
    ):
        """property_idで正しくフィルタリング"""
        mock_data_loader.load.return_value = sample_real_estate_data

        cashflow = analyzer.calculate_cashflow(
            "property_002", date(2024, 7, 1), date(2024, 7, 31)
        )

        # property_002の収入: 50000（駐車場収入）
        assert cashflow.income == Decimal("50000.00")


class TestRealEstateExpenseExtraction:
    """不動産支出抽出テスト"""

    def test_extract_expense_with_keywords(
        self, analyzer, mock_data_loader, sample_real_estate_data
    ):
        """不動産支出キーワードで正しく抽出"""
        mock_data_loader.load.return_value = sample_real_estate_data

        cashflow = analyzer.calculate_cashflow(
            "property_001", date(2024, 7, 1), date(2024, 7, 31)
        )

        # property_001の支出: 20000（管理費）+ 10000（修繕費）= 30000
        assert cashflow.expense == Decimal("30000.00")

    def test_extract_negative_amounts_only(
        self, analyzer, mock_data_loader, sample_real_estate_data
    ):
        """負の金額のみを支出として抽出"""
        mock_data_loader.load.return_value = sample_real_estate_data

        cashflow = analyzer.calculate_cashflow(
            "property_001", date(2024, 7, 1), date(2024, 7, 31)
        )

        # 正の金額は支出に含まれない
        assert cashflow.expense >= 0

    def test_expense_absolute_value(
        self, analyzer, mock_data_loader, sample_real_estate_data
    ):
        """支出は絶対値で保存される"""
        mock_data_loader.load.return_value = sample_real_estate_data

        cashflow = analyzer.calculate_cashflow(
            "property_002", date(2024, 7, 1), date(2024, 7, 31)
        )

        # property_002の支出: 5000（固定資産税）の絶対値
        assert cashflow.expense == Decimal("5000.00")


class TestNetCashflowCalculation:
    """純キャッシュフロー計算テスト"""

    def test_positive_cashflow(
        self, analyzer, mock_data_loader, sample_real_estate_data
    ):
        """黒字キャッシュフロー"""
        mock_data_loader.load.return_value = sample_real_estate_data

        cashflow = analyzer.calculate_cashflow(
            "property_001", date(2024, 7, 1), date(2024, 7, 31)
        )

        # 純キャッシュフロー: 100000 - 30000 = 70000
        assert cashflow.net_cashflow == Decimal("70000.00")

    def test_negative_cashflow(self, analyzer, mock_data_loader):
        """赤字キャッシュフロー"""
        data = pd.DataFrame(
            {
                "日付": pd.to_datetime(["2024-07-01", "2024-07-05"]),
                "金額（円）": [10000, -50000],
                "計算対象": [1, 1],
                "大項目": ["不動産", "住宅"],
                "中項目": ["家賃収入", "修繕費"],
                "備考": ["property_001", "property_001"],
            }
        )
        mock_data_loader.load.return_value = data

        cashflow = analyzer.calculate_cashflow(
            "property_001", date(2024, 7, 1), date(2024, 7, 31)
        )

        # 純キャッシュフロー: 10000 - 50000 = -40000
        assert cashflow.net_cashflow == Decimal("-40000.00")

    def test_zero_income_case(self, analyzer, mock_data_loader):
        """収入がない場合"""
        data = pd.DataFrame(
            {
                "日付": pd.to_datetime(["2024-07-01"]),
                "金額（円）": [-20000],
                "計算対象": [1],
                "大項目": ["住宅"],
                "中項目": ["管理費"],
                "備考": ["property_001"],
            }
        )
        mock_data_loader.load.return_value = data

        cashflow = analyzer.calculate_cashflow(
            "property_001", date(2024, 7, 1), date(2024, 7, 31)
        )

        assert cashflow.income == Decimal("0.00")
        assert cashflow.net_cashflow == Decimal("-20000.00")


class TestROICalculation:
    """ROI計算テスト"""

    def test_roi_calculation_basic(
        self, analyzer, mock_data_loader, sample_real_estate_data
    ):
        """基本的なROI計算"""
        mock_data_loader.load.return_value = sample_real_estate_data

        cashflow = analyzer.calculate_cashflow(
            "property_001", date(2024, 7, 1), date(2024, 7, 31)
        )

        # 月次キャッシュフロー: 70000
        # 年換算: 70000 * 12 = 840000
        # ROI: (840000 / 30000000) * 100 = 2.8%
        expected_roi = Decimal("2.80")
        assert abs(cashflow.roi - expected_roi) < Decimal("0.01")

    def test_roi_with_negative_cashflow(self, analyzer, mock_data_loader):
        """赤字の場合もROI計算する"""
        data = pd.DataFrame(
            {
                "日付": pd.to_datetime(["2024-07-01", "2024-07-05"]),
                "金額（円）": [10000, -50000],
                "計算対象": [1, 1],
                "大項目": ["不動産", "住宅"],
                "中項目": ["家賃収入", "修繕費"],
                "備考": ["property_001", "property_001"],
            }
        )
        mock_data_loader.load.return_value = data

        cashflow = analyzer.calculate_cashflow(
            "property_001", date(2024, 7, 1), date(2024, 7, 31)
        )

        # 月次キャッシュフロー: -40000
        # 年換算: -40000 * 12 = -480000
        # ROI: (-480000 / 30000000) * 100 = -1.6%
        expected_roi = Decimal("-1.60")
        assert abs(cashflow.roi - expected_roi) < Decimal("0.01")

    def test_roi_with_different_initial_investment(
        self, analyzer, mock_data_loader, sample_real_estate_data
    ):
        """異なる初期投資額でROI計算"""
        mock_data_loader.load.return_value = sample_real_estate_data

        cashflow = analyzer.calculate_cashflow(
            "property_002", date(2024, 7, 1), date(2024, 7, 31)
        )

        # 月次キャッシュフロー: 50000 - 5000 = 45000
        # 年換算: 45000 * 12 = 540000
        # ROI: (540000 / 5000000) * 100 = 10.8%
        expected_roi = Decimal("10.80")
        assert abs(cashflow.roi - expected_roi) < Decimal("0.01")


class TestPropertyDatabaseLoading:
    """物件データベース読み込みテスト"""

    def test_load_property_database_success(
        self, mock_income_analyzer, mock_data_loader, property_database_json
    ):
        """正常に物件データベースを読み込む"""
        with patch(
            "builtins.open", mock_open(read_data=property_database_json)
        ):
            analyzer = RealEstateCashflowAnalyzer(
                mock_income_analyzer, mock_data_loader
            )

            assert "property_001" in analyzer._properties
            assert "property_002" in analyzer._properties
            assert (
                analyzer._properties["property_001"]["initial_investment"] == 30000000
            )

    def test_missing_property_raises_error(
        self, analyzer, mock_data_loader, sample_real_estate_data
    ):
        """存在しない物件IDでエラー"""
        mock_data_loader.load.return_value = sample_real_estate_data

        with pytest.raises(ValueError, match="Property ID .* not found"):
            analyzer.calculate_cashflow(
                "property_999", date(2024, 7, 1), date(2024, 7, 31)
            )


class TestDateRangeFiltering:
    """日付範囲フィルタリングテスト"""

    def test_filter_by_date_range(
        self, analyzer, mock_data_loader, sample_real_estate_data
    ):
        """指定期間内のデータのみ使用"""
        mock_data_loader.load.return_value = sample_real_estate_data

        # 7月前半のみ
        cashflow = analyzer.calculate_cashflow(
            "property_001", date(2024, 7, 1), date(2024, 7, 10)
        )

        # 7月10日以前: 家賃収入100000（7/5）、管理費20000（7/10）
        assert cashflow.income == Decimal("100000.00")
        assert cashflow.expense == Decimal("20000.00")


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
        assert result["roi"] == 2.8
        assert isinstance(result["roi"], float)


class TestEdgeCases:
    """エッジケーステスト"""

    def test_no_data_in_period(self, analyzer, mock_data_loader):
        """期間内にデータがない場合"""
        mock_data_loader.load.return_value = pd.DataFrame()

        cashflow = analyzer.calculate_cashflow(
            "property_001", date(2024, 1, 1), date(2024, 1, 31)
        )

        assert cashflow.income == Decimal("0.00")
        assert cashflow.expense == Decimal("0.00")
        assert cashflow.net_cashflow == Decimal("0.00")
        assert cashflow.roi == Decimal("0.00")

    def test_no_property_id_in_remarks(self, analyzer, mock_data_loader):
        """備考欄にproperty_idがない場合は除外"""
        data = pd.DataFrame(
            {
                "日付": pd.to_datetime(["2024-07-01"]),
                "金額（円）": [100000],
                "計算対象": [1],
                "大項目": ["不動産"],
                "中項目": ["家賃収入"],
                "備考": [""],  # property_id なし
            }
        )
        mock_data_loader.load.return_value = data

        cashflow = analyzer.calculate_cashflow(
            "property_001", date(2024, 7, 1), date(2024, 7, 31)
        )

        # property_idが一致しないため収入ゼロ
        assert cashflow.income == Decimal("0.00")
