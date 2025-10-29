# リファクタリング提案書

**作成日**: 2025-10-28  
**対象**: Household MCP Server  
**ステータス**: 提案

---

## 1. エグゼクティブサマリー

現在の実装は機能的には完成していますが、以下の観点から改善の余地があります：

- **保守性**: 一部のファイルが大きく（640行超）、責務が混在
- **テスタビリティ**: グローバル状態への依存が一部存在
- **拡張性**: 画像生成機能追加に向けた構造改善の必要性
- **コード品質**: 長い行やマジックナンバーの存在

---

## 2. 現状分析

### 2.1 ファイルサイズ分析

| ファイル | 行数 | 評価 | 備考 |
|---------|------|------|------|
| chart_generator.py | 641 | 🟡 やや大 | メソッド数20、適切に分割されている |
| server.py | 467 | 🟢 適切 | MCPエンドポイント定義が中心 |
| dataloader.py | 225 | 🟢 適切 | 単一責任を守っている |
| trends.py | 234 | 🟢 適切 | 分析ロジックに集中 |

### 2.2 主要な問題点

#### 問題1: BudgetAnalyzer のグローバルインスタンス

**場所**: `src/household_mcp/server.py:271-273`

```python
# グローバルインスタンス
analyzer: Optional[BudgetAnalyzer] = None
```

**問題点**:
- グローバル状態による副作用
- テストでのモック困難
- スレッドセーフでない

**影響度**: 🟡 中

#### 問題2: BudgetAnalyzer の重複機能

**場所**: `src/household_mcp/server.py:207-269`

**問題点**:
- `HouseholdDataLoader` と機能重複
- 独自の CSV 読み込みロジック
- `monthly_summary` ツールのみで使用

**影響度**: 🟡 中

#### 問題3: 長い行（E501）

**場所**: server.py 6箇所

**問題点**:
- flake8 警告
- 可読性の低下

**影響度**: 🟢 低

#### 問題4: category_analysis の複雑な例外処理

**場所**: `src/household_mcp/server.py:294-416`

**問題点**:
- 123行の長い関数
- 複数の責務（データ取得・集計・フォーマット）
- ネストが深い

**影響度**: 🟡 中

#### 問題5: ChartGenerator のフォント検出ロジック

**場所**: `src/household_mcp/visualization/chart_generator.py:233-341`

**問題点**:
- 3つのメソッドに分割（良い設計）
- プラットフォーム固有パスのハードコード

**影響度**: 🟢 低（設計は良好）

---

## 3. リファクタリング提案

### 優先度 HIGH

#### 提案1: BudgetAnalyzer の統合または削除

**目的**: コードの重複排除、保守性向上

**アプローチ**:

**Option A: HouseholdDataLoader への統合**
```python
# dataloader.py に追加
class HouseholdDataLoader:
    def get_monthly_summary(self, year: int, month: int) -> dict:
        """月次サマリを返す（BudgetAnalyzer の機能を統合）"""
        df = self.load_csv_from_month(year, month)
        # 集計ロジックを実装
        ...
```

**Option B: 独立したサービスクラスとして再設計**
```python
# services/summary_service.py
class MonthlySummaryService:
    def __init__(self, data_loader: HouseholdDataLoader):
        self.data_loader = data_loader
    
    def get_summary(self, year: int, month: int) -> dict:
        # DI を活用したテスタブルな設計
        ...
```

**推奨**: Option A（既存の DataLoader に統合）

**工数**: 0.5d

---

#### 提案2: category_analysis の分割

**目的**: 関数の複雑度削減、テスタビリティ向上

**アプローチ**:

```python
# tools/category_analysis_tool.py
class CategoryAnalysisTool:
    def __init__(self, data_loader: HouseholdDataLoader):
        self.data_loader = data_loader
        self.analyzer = CategoryTrendAnalyzer(loader=data_loader)
    
    def analyze(self, category: str, months: int) -> dict:
        """主要ロジック"""
        available_months = self._get_available_months(months)
        metrics = self._calculate_metrics(category, available_months)
        return self._format_response(category, metrics)
    
    def _get_available_months(self, months: int) -> list:
        """利用可能月の取得"""
        ...
    
    def _calculate_metrics(self, category: str, months: list) -> list:
        """メトリクス計算"""
        ...
    
    def _format_response(self, category: str, metrics: list) -> dict:
        """レスポンス整形"""
        ...
```

**メリット**:
- 各メソッドが30行以内
- 単体テスト可能
- 責務が明確

**工数**: 0.5d

---

### 優先度 MEDIUM

#### 提案3: 設定値の外部化

**目的**: マジックナンバー削減、設定の一元管理

**アプローチ**:

```python
# config.py
@dataclass
class ServerConfig:
    data_dir: str = "data"
    default_analysis_months: int = 3
    cache_size: int = 50
    cache_ttl: int = 3600

@dataclass
class ChartConfig:
    default_size: str = "800x600"
    default_dpi: int = 150
    chunk_size: int = 8192
    colors: list[str] = field(default_factory=lambda: [
        '#FF6B6B', '#4ECDC4', '#45B7D1', ...
    ])
```

**工数**: 0.3d

---

#### 提案4: エラーハンドリングの統一

**目的**: 一貫性のあるエラーレスポンス

**アプローチ**:

```python
# utils/error_handler.py
class MCPErrorHandler:
    @staticmethod
    def handle_data_source_error(e: DataSourceError, context: dict) -> dict:
        """DataSourceError の標準処理"""
        return {
            "error": "データソースエラー",
            "message": str(e),
            "context": context,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def handle_validation_error(e: ValidationError, context: dict) -> dict:
        """ValidationError の標準処理"""
        ...
```

**工数**: 0.3d

---

### 優先度 LOW

#### 提案5: 長い行の修正

**目的**: flake8 警告の解消

**アプローチ**:

```python
# Before
"""MCP Server for household budget analysis with natural language interface and trend analysis."""

# After
"""MCP Server for household budget analysis.

Provides natural language interface and trend analysis capabilities.
"""
```

**工数**: 0.1d

---

#### 提案6: テストカバレッジの向上

**現状**: trends.py 88%, dataloader.py 93%

**目標**: 全モジュール 90% 以上

**アプローチ**:
- エッジケースのテスト追加
- 統合テストの拡充

**工数**: 1.0d

---

## 4. 実装計画

### フェーズ1: 高優先度リファクタリング（Week 8）

- [ ] 提案1: BudgetAnalyzer 統合（0.5d）
- [ ] 提案2: category_analysis 分割（0.5d）

**合計**: 1.0d

### フェーズ2: 中優先度改善（Week 9）

- [ ] 提案3: 設定値外部化（0.3d）
- [ ] 提案4: エラーハンドリング統一（0.3d）
- [ ] 提案5: 長い行の修正（0.1d）

**合計**: 0.7d

### フェーズ3: テスト強化（Week 10）

- [ ] 提案6: テストカバレッジ向上（1.0d）

**合計**: 1.0d

**全体工数**: 2.7d

---

## 5. リスク評価

| リスク | 確率 | 影響 | 対策 |
|--------|------|------|------|
| 既存機能の破壊 | 低 | 高 | 既存テストで継続的検証 |
| リファクタリング工数超過 | 中 | 中 | フェーズ分割、優先順位明確化 |
| 新機能開発の遅延 | 低 | 中 | 高優先度のみ先行実施 |

---

## 6. 非推奨事項

以下は**リファクタリング不要**と判断：

1. **ChartGenerator の構造**
   - 理由: 適切に分割済み、SRP を守っている
   - 現状維持を推奨

2. **streaming パッケージ**
   - 理由: 新規実装で設計が良好
   - 現状維持を推奨

3. **HouseholdDataLoader**
   - 理由: キャッシュ機構含め良好な設計
   - 現状維持を推奨

---

## 7. 推奨アクション

### 即座に実施すべき

1. **提案5（長い行の修正）**: 影響小、工数0.1d
   - 今すぐ実施可能

### 画像生成機能実装前に実施すべき

2. **提案3（設定値外部化）**: 新機能で設定が増える前に
3. **提案4（エラーハンドリング統一）**: 新ツールで一貫性確保

### 時間があれば実施

4. **提案1、2（構造改善）**: 保守性向上
5. **提案6（テスト強化）**: 品質保証

---

## 8. 結論

現在の実装品質は**良好**です。クリティカルな問題はありませんが、以下を推奨します：

**短期（今週）**:
- ✅ 長い行の修正（0.1d）

**中期（来週）**:
- 設定値外部化（0.3d）
- エラーハンドリング統一（0.3d）

**長期（余裕があれば）**:
- BudgetAnalyzer 統合（0.5d）
- category_analysis 分割（0.5d）
- テストカバレッジ向上（1.0d）

**優先順位**: 新機能実装 > リファクタリング

---

## 9. 付録: コード品質メトリクス

### 現状

| 指標 | 値 | 目標 | 状態 |
|------|------|------|------|
| テストカバレッジ（平均） | 88-93% | 90% | 🟢 良好 |
| flake8 警告 | 6件 | 0件 | 🟡 改善可能 |
| 最大関数長 | 123行 | 50行 | 🟡 改善推奨 |
| ファイル数 | 適切 | - | 🟢 良好 |
| 依存関係 | クリーン | - | 🟢 良好 |

### 改善後の予測

| 指標 | 値 | 改善 |
|------|------|------|
| flake8 警告 | 0件 | ✅ |
| 最大関数長 | 40行 | ✅ |
| テストカバレッジ | 95% | ✅ |
