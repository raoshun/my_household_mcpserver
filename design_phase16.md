# Phase 16: 収入分析・強化FIRE計算 設計書

**作成日**: 2025-11-16  
**対象要件**: FR-032, FR-033, FR-034  
**実装期間**: 2-3週間（11-14日）

---

## 1. 概要

Phase 15 までに実装した支出ベースのFIRE計算を拡張し、収入データを活用した総合的なキャッシュフロー分析とFIREシミュレーションを実現する。

**目標**:

- CSVデータから収入を5カテゴリに自動分類（給与、事業、不動産、配当、その他）
- 月次/年次の貯蓄率を計算し、資産形成ペースを可視化
- 不動産キャッシュフロー（収入 - 支出）とROIを計算
- 4種類のFIREタイプ（標準/コースト/バリスタ/サイド）をサポート
- 受動的収入を考慮した目標資産額の再計算
- What-Ifシミュレーション機能の提供

---

## 2. アーキテクチャ

```text
┌────────────────────────────────────────────────────────────┐
│                   収入分析・FIRE強化レイヤー                   │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌─────────────────┐  ┌──────────────────────────┐       │
│  │ IncomeAnalyzer  │  │ SavingsRateCalculator   │       │
│  │                 │  │                          │       │
│  │ • 収入抽出      │  │ • 貯蓄率計算             │       │
│  │ • 5カテゴリ分類 │  │ • 可処分所得計算         │       │
│  │ • 月次/年次集計 │  │ • 変動費率計算           │       │
│  └────────┬────────┘  └───────────┬──────────────┘       │
│           │                        │                      │
│  ┌────────┴────────────────────────┴──────────────┐       │
│  │    RealEstateCashflowAnalyzer                  │       │
│  │                                                 │       │
│  │  • 不動産収入・支出の照合                       │       │
│  │  • ネットキャッシュフロー計算                   │       │
│  │  • ROI計算（物件別）                            │       │
│  └─────────────────┬───────────────────────────────┘       │
│                    │                                      │
│  ┌─────────────────┴───────────────────────────────┐       │
│  │    EnhancedFIRESimulator                        │       │
│  │                                                  │       │
│  │  • 4種類のFIREタイプサポート                     │       │
│  │  • 受動的収入考慮                                │       │
│  │  • 複数シナリオ比較                              │       │
│  │  • What-Ifシミュレーション                       │       │
│  └──────────────────────────────────────────────────┘       │
│                                                            │
└────────────────────────────────────────────────────────────┘
                             │
                             ▼
         ┌────────────────────────────────────┐
         │  HouseholdDataLoader (既存)        │
         │  • CSV読み込み                     │
         │  • データキャッシング               │
         └────────────────────────────────────┘
                             │
                             ▼
         ┌────────────────────────────────────┐
         │  SQLite Database                   │
         │  • income_snapshots (新規)         │
         │  • fire_asset_snapshots (既存)     │
         │  • fi_progress_cache (既存)        │
         └────────────────────────────────────┘
```

---

## 3. 主要クラス設計

### 3.1 IncomeAnalyzer

**ファイル**: `backend/src/household_mcp/analysis/income_analyzer.py`

**責務**: CSVデータから収入を抽出・分類し、月次/年次サマリーを生成

```python
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional
from datetime import date
import pandas as pd

@dataclass
class IncomeCategory:
    """収入カテゴリ定義"""
    SALARY = "給与所得"
    BUSINESS = "事業所得"
    REAL_ESTATE = "不動産所得"
    DIVIDEND = "配当・利子所得"
    OTHER = "その他収入"

@dataclass
class IncomeSummary:
    """収入サマリー"""
    year: int
    month: Optional[int]  # None = 年次サマリー
    total_income: Decimal
    category_breakdown: Dict[str, Decimal]  # カテゴリ名 -> 金額
    category_ratios: Dict[str, Decimal]  # カテゴリ名 -> 構成比率(%)
    previous_period_change: Optional[Decimal]  # 前月比/前年比(%)
    average_monthly: Optional[Decimal]  # 月平均（年次のみ）

class IncomeAnalyzer:
    """収入分析エンジン"""

    def __init__(self, data_loader: HouseholdDataLoader):
        self.data_loader = data_loader
        self.category_rules = self._load_category_rules()

    def extract_income_records(
        self,
        start_date: date,
        end_date: date
    ) -> pd.DataFrame:
        """
        指定期間の収入レコードを抽出

        条件:
        - 金額（円）> 0
        - 計算対象 = 1
        """
        pass

    def classify_income(self, record: pd.Series) -> str:
        """
        収入レコードを5カテゴリに分類

        分類ルール:
        1. 大項目 or 中項目に「給与」「賞与」→ 給与所得
        2. 大項目 or 中項目に「事業」→ 事業所得
        3. 大項目 or 中項目に「不動産」「家賃収入」→ 不動産所得
        4. 大項目 or 中項目に「配当」「利子」「分配金」→ 配当・利子所得
        5. その他 → その他収入
        """
        pass

    def get_monthly_summary(
        self,
        year: int,
        month: int
    ) -> IncomeSummary:
        """月次収入サマリーを取得"""
        pass

    def get_annual_summary(self, year: int) -> IncomeSummary:
        """年次収入サマリーを取得"""
        pass

    def _load_category_rules(self) -> Dict:
        """
        カテゴリ分類ルールを income_categories.json から読み込み

        フォーマット:
        {
          "salary": {
            "keywords": ["給与", "賞与", "ボーナス"],
            "large_categories": ["給与"],
            "medium_categories": ["給与", "賞与"]
          },
          ...
        }
        """
        pass
```

**パフォーマンス要件** (NFR-037):

- 月次サマリー計算: 1秒以内
- 年次サマリー計算: 1秒以内
- キャッシング: 1時間有効（NFR-040）

---

### 3.2 SavingsRateCalculator

**ファイル**: `backend/src/household_mcp/analysis/savings_rate_calculator.py`

**責務**: 収入・支出データから貯蓄率と関連指標を計算

```python
@dataclass
class SavingsMetrics:
    """貯蓄関連メトリクス"""
    year: int
    month: Optional[int]
    income: Decimal  # 収入
    expense: Decimal  # 支出
    savings: Decimal  # 貯蓄額（収入 - 支出）
    savings_rate: Decimal  # 貯蓄率(%)
    disposable_income: Decimal  # 可処分所得（収入 - 固定費）
    fixed_costs: Decimal  # 固定費
    variable_costs: Decimal  # 変動費
    variable_cost_ratio: Decimal  # 変動費率(%)

class SavingsRateCalculator:
    """貯蓄率計算エンジン"""

    def __init__(
        self,
        income_analyzer: IncomeAnalyzer,
        data_loader: HouseholdDataLoader
    ):
        self.income_analyzer = income_analyzer
        self.data_loader = data_loader

    def calculate_monthly_savings_rate(
        self,
        year: int,
        month: int
    ) -> SavingsMetrics:
        """
        月次貯蓄率を計算

        計算式:
        - 貯蓄額 = 収入 - 支出
        - 貯蓄率 = (貯蓄額 / 収入) × 100
        - 可処分所得 = 収入 - 固定費
        - 変動費率 = (変動費 / 可処分所得) × 100
        """
        pass

    def get_savings_rate_trend(
        self,
        start_date: date,
        end_date: date
    ) -> List[SavingsMetrics]:
        """期間の貯蓄率推移を取得"""
        pass

    def classify_cost_type(self, record: pd.Series) -> str:
        """
        支出を固定費・変動費に分類

        固定費カテゴリ:
        - 住宅（家賃、ローン）
        - 水道光熱費
        - 通信費
        - 保険
        """
        pass
```

**数値精度要件** (NFR-038):

- 貯蓄率: 小数第2位まで（例: 25.34%）

---

### 3.3 RealEstateCashflowAnalyzer

**ファイル**: `backend/src/household_mcp/analysis/real_estate_cashflow_analyzer.py`

**責務**: 不動産収入・支出を照合し、キャッシュフローとROIを計算

```python
@dataclass
class RealEstateCashflow:
    """不動産キャッシュフロー"""
    property_id: Optional[str]  # 物件ID（複数物件対応）
    year: int
    month: Optional[int]
    income: Decimal  # 不動産収入
    expense: Decimal  # 不動産支出
    net_cashflow: Decimal  # ネットキャッシュフロー
    roi: Optional[Decimal]  # ROI(%)

class RealEstateCashflowAnalyzer:
    """不動産キャッシュフロー分析エンジン"""

    def __init__(
        self,
        income_analyzer: IncomeAnalyzer,
        data_loader: HouseholdDataLoader
    ):
        self.income_analyzer = income_analyzer
        self.data_loader = data_loader
        self.property_db = self._load_property_database()

    def calculate_cashflow(
        self,
        start_date: date,
        end_date: date,
        property_id: Optional[str] = None
    ) -> RealEstateCashflow:
        """
        不動産キャッシュフローを計算

        計算:
        - 不動産収入: 大項目「不動産」の正の金額
        - 不動産支出: 大項目「住宅」の負の金額
        - ネットキャッシュフロー = 収入 - 支出
        """
        pass

    def calculate_roi(
        self,
        property_id: str,
        year: int
    ) -> Decimal:
        """
        不動産ROIを計算

        計算式:
        ROI = (年間ネットキャッシュフロー / 初期投資額) × 100
        """
        pass

    def _load_property_database(self) -> Dict:
        """
        物件情報を property_database.json から読み込み

        フォーマット:
        {
          "property_001": {
            "name": "マンションA",
            "initial_investment": 30000000,
            "purchase_date": "2020-04-01"
          }
        }
        """
        pass
```

**パフォーマンス要件** (NFR-041):

- 対応物件数: 最大10件

---

### 3.4 EnhancedFIRESimulator

**ファイル**: `backend/src/household_mcp/analysis/enhanced_fire_simulator.py`

**責務**: 収入データを活用した高度なFIREシミュレーション

```python
from enum import Enum

class FIREType(Enum):
    """FIREタイプ"""
    STANDARD = "標準FIRE"
    COAST = "コーストFIRE"
    BARISTA = "バリスタFIRE"
    SIDE = "サイドFIRE"

@dataclass
class FIREScenario:
    """FIREシナリオ設定"""
    name: str
    fire_type: FIREType
    initial_assets: Decimal
    monthly_savings: Decimal
    annual_return_rate: Decimal
    inflation_rate: Decimal
    passive_income: Decimal
    part_time_income: Optional[Decimal]
    side_income: Optional[Decimal]
    expense_growth_rate: Decimal

@dataclass
class FIRESimulationResult:
    """FIREシミュレーション結果"""
    scenario_name: str
    fire_type: FIREType
    target_assets: Decimal
    months_to_fire: int
    achievement_date: str
    total_savings_needed: Decimal
    asset_timeline: List[Dict]
    risk_assessment: str

class EnhancedFIRESimulator:
    """強化FIREシミュレーター"""

    def calculate_fire_target(
        self,
        fire_type: FIREType,
        annual_expense: Decimal,
        passive_income: Decimal = Decimal("0"),
        **kwargs
    ) -> Decimal:
        """
        FIREタイプ別の目標資産額を計算

        計算式:
        - 標準FIRE: 年間支出 × 25
        - コーストFIRE: (老後必要額 - 現資産の将来価値) を逆算
        - バリスタFIRE: (年間支出 - パートタイム収入) × 25
        - サイドFIRE: (年間支出 - 副業収入) × 25

        受動的収入考慮:
        - 必要資産 = (年間支出 - 年間受動的収入) × 25
        """
        pass

    def simulate_scenarios(
        self,
        scenarios: List[FIREScenario]
    ) -> List[FIRESimulationResult]:
        """複数シナリオを一括シミュレーション"""
        pass

    def what_if_simulation(
        self,
        base_scenario: FIREScenario,
        changes: Dict[str, Decimal]
    ) -> Dict:
        """What-Ifシミュレーション"""
        pass
```

**パフォーマンス要件** (NFR-039):

- 最大5シナリオを3秒以内に計算

---

## 4. データベーススキーマ

### 4.1 income_snapshots テーブル（新規）

```sql
CREATE TABLE IF NOT EXISTS income_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_date TEXT NOT NULL UNIQUE,
    salary_income INTEGER NOT NULL DEFAULT 0,
    business_income INTEGER NOT NULL DEFAULT 0,
    real_estate_income INTEGER NOT NULL DEFAULT 0,
    dividend_income INTEGER NOT NULL DEFAULT 0,
    other_income INTEGER NOT NULL DEFAULT 0,
    total_income INTEGER NOT NULL,
    savings_rate REAL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_income_snapshot_date ON income_snapshots(snapshot_date);
```

---

## 5. MCPツール定義

### 5.1 収入分析ツール

```python
@mcp.tool()
def get_income_summary(year: int, month: int) -> dict:
    """月次収入サマリーを取得"""
    pass

@mcp.tool()
def get_annual_income_summary(year: int) -> dict:
    """年次収入サマリーを取得"""
    pass
```

### 5.2 貯蓄率分析ツール

```python
@mcp.tool()
def get_savings_rate(year: int, month: int) -> dict:
    """月次貯蓄率を取得"""
    pass

@mcp.tool()
def get_savings_rate_trend(start_date: str, end_date: str) -> dict:
    """貯蓄率推移を取得"""
    pass
```

### 5.3 不動産キャッシュフローツール

```python
@mcp.tool()
def get_real_estate_cashflow(
    start_date: str,
    end_date: str,
    property_id: Optional[str] = None
) -> dict:
    """不動産キャッシュフローを取得"""
    pass
```

### 5.4 強化FIREシミュレーションツール

```python
@mcp.tool()
def simulate_fire_scenarios(scenarios: List[dict]) -> dict:
    """複数シナリオを一括シミュレーション"""
    pass

@mcp.tool()
def what_if_fire_simulation(base_scenario: dict, changes: dict) -> dict:
    """What-Ifシミュレーションを実行"""
    pass
```

### 5.5 統合レポートツール

```python
@mcp.tool()
def generate_comprehensive_cashflow_report(
    year: int,
    format: str = "markdown"
) -> dict:
    """年次総合キャッシュフローレポートを生成"""
    pass
```

---

## 6. テスト戦略

### 6.1 単体テスト（80件予定）

- `test_income_analyzer.py`: 20テスト
- `test_savings_rate_calculator.py`: 15テスト
- `test_real_estate_cashflow.py`: 15テスト
- `test_enhanced_fire_simulator.py`: 30テスト

### 6.2 統合テスト（30件予定）

- MCP Tool Integration: 15テスト
- REST API Integration: 15テスト

### 6.3 E2Eテスト（10件予定）

- 総合レポート生成
- FIREシミュレーション画面操作

**カバレッジ目標**: 80% 以上

---

## 7. 実装スケジュール

### Phase 1: 基礎分析機能（3-4日）

- TASK-2001: IncomeAnalyzer 基礎実装（1.0d）
- TASK-2002: SavingsRateCalculator 実装（1.0d）
- TASK-2003: RealEstateCashflowAnalyzer 実装（1.0d）
- TASK-2004: 単体テスト（1.0d）

### Phase 2: FIRE計算強化（4-5日）

- TASK-2005: EnhancedFIRESimulator 基礎実装（1.5d）
- TASK-2006: 4種類のFIREタイプサポート（1.0d）
- TASK-2007: シナリオ比較機能（1.0d）
- TASK-2008: 単体テスト（1.0d）

### Phase 3: 高度機能・統合（4-5日）

- TASK-2009: What-Ifシミュレーション（1.0d）
- TASK-2010: MCPツール実装（1.0d）
- TASK-2011: REST API実装（0.75d）
- TASK-2012: 統合テスト（1.0d）
- TASK-2013: ドキュメント整備（0.75d）

**合計**: 11-14日（2-3週間）
