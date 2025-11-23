# 家計簿分析 MCP サーバー設計書

- **バージョン**: 1.0.0（フェーズ16: 収入分析・強化FIRE計算）
- **更新日**: 2025-11-17
- **作成者**: GitHub Copilot (AI assistant)
- **対象要件**: [requirements.md](./requirements.md) v1.6 に記載の FR-032〜FR-037、NFR-037〜NFR-042
- **実装状況**:
  - Phase 15 完了: テスト 48/48 PASSED (100%), カバレッジ 76%, パフォーマンス < 500ms ✅
  - Phase 16 計画中: 収入分析、貯蓄率計算、不動産キャッシュフロー、強化FIREシミュレーション

---

## 1. システムアーキテクチャ

### 1.1 全体像

```text
┌──────────────┐   MCPプロトコル   ┌─────────────────────┐
│  LLMクライアント │ ◄─────────────► │ 家計簿分析 MCP サーバ │
└──────────────┘                  └────────┬────────────┘
                                                │
                                                │ pandas DataFrame
                                                ▼
                                      ┌────────────────────────┐
                                      │  CSV データ / ローカルFS │
                                      └────────────────────────┘
```

### Phase 16 更新点（要約） — FR-035, FR-036, FR-037

- 公開ファサード: 分析系ツールは `household_mcp.tools.analysis_tools` に統一（FR-035）。
  - 旧 `household_mcp.tools.phase16_tools` は削除済み（2025-11-17、後方互換性不要と判断）。
  - Web ルータ/ツール登録は `analysis_tools` を参照。
- FIRE What-If: `annual_expense` を第一級の入力として必須化（FR-036）。
  - `FIREScenario` に `annual_expense: Decimal` を追加／必須。
  - `EnhancedFIRESimulator.simulate_scenario` / `what_if_simulation` は `annual_expense` を `calculate_fire_target` に渡す。
  - What-If の変更サマリ（before/after/impact）を返す最小限の構造を維持。
  - Pydantic の API 入力モデルでも `annual_expense` を必須・>0 検証。
- 非同期画像ストリーミング安定化（FR-037）: FastAPI / pytest(anyio) / MCP 実行環境でイベントループ競合を排除し安定したチャンク配信を保証。
  - ループ検出ロジックの単純化（`get_running_loop()` 成功時のみ async generator、失敗時は同期フォールバックか削除方針を選択）。
  - 同期フォールバック `stream_bytes_sync` は任意機能化（削除しても API は壊れない設計）。
  - 5 並行リクエストで 0.5s 以内レスポンス（FR-016 性能整合）。
  - テスト分離: async テストファイルと（残すなら）sync テストファイルで anyio マーカーのスコープ最適化。

---

## Phase 15 - 高度な分析機能（詳細設計）

以下は `design_phase15.md` から統合した Phase 15 の詳細設計です。

### 概要

Phase 14 の完了を受け、Phase 15 では次の 3 つの高度な分析ツールを実装します。

1. FIRE 計算エンジン（金融独立予測）
2. シナリオ分析（支出削減・収入増加の比較）
3. 支出パターン分析（定期・変動・異常支出の分類、季節性/トレンド検出）

これらは MCP リソースと HTTP API として公開し、統合テストで品質を検証します。

---

### 1. FIRE 計算エンジン（設計要約）

- モジュール: `src/household_mcp/analysis/fire_calculator.py`
- 主要機能: `calculate_fire_index(...)` による複利・インフレ考慮のシミュレーション
- 出力: 到達予定年月、月次資産推移、複数シナリオ（悲観/中立/楽観）

計算の要点:

- 月利 = (1 + 年利)^(1/12) - 1
- 資産推移を月単位で計算し、目標資産到達を検出

返却型（要約）:

```python
class FireCalculationResult:
    scenario: str
    target_assets: Decimal
    months_to_fire: int
    target_year_month: str
    asset_timeline: List[Dict]
```

---

### 2. シナリオ分析（設計要約）

- モジュール: `src/household_mcp/analysis/scenario_simulator.py`
- クラス: `ScenarioSimulator`（複数シナリオのシミュレーション・比較・推奨）
- 主要出力: 各シナリオの新しい月貯蓄、短縮月数、ROI（効果/難易度）

主要型（抜粋）:

```python
class ScenarioConfig:
    name: str
    type: ScenarioType
    category: Optional[str]
    reduction_pct: Optional[Decimal]
    income_increase: Optional[Decimal]

class ScenarioResult:
    scenario_name: str
    new_monthly_savings: Decimal
    months_to_fire: int
    months_saved: int
    difficulty_score: int
    roi_score: Decimal
```

---

### 3. 支出パターン分析（設計要約）

- モジュール: `src/household_mcp/analysis/expense_pattern_analyzer.py`
- 主要機能: `classify_expenses`, `detect_seasonality`, `calculate_trend`
- 分類ルール（簡略）:
  - 定期支出: 3 か月以上・変動率小
  - 変動支出: 平均 ± 2σ の範囲
  - 異常支出: 平均 + 2σ を超える低頻度の出費

返却型（抜粋）:

```python
class ExpenseClassification:
    recurring: List[ExpenseRecord]
    variable: List[ExpenseRecord]
    anomalies: List[ExpenseRecord]

class SeasonalityResult:
    monthly_indices: Dict[int, Decimal]
    peak_month: int
    trough_month: int

class TrendResult:
    slope: Decimal
    r_squared: Decimal
    trend_direction: str
```

---

### MCP リソース & HTTP API 拡張（要約）

追加リソース（server.py）:

- `data://financial_independence` → FIRE 計算結果
- `data://scenarios` → シナリオ分析結果
- `data://expense_patterns` → 支出パターン分析

追加ツール（MCP tool）:

- `calculate_fire_index(...)`
- `simulate_scenarios(...)`
- `analyze_spending_patterns()`

HTTP API エンドポイント（FastAPI）:

- `GET /api/v1/financial-independence`
- `POST /api/v1/scenarios`
- `GET /api/v1/spending-patterns`

---

### 実装スケジュール（要約）

| タスク    |               内容 |  日数 |     テスト |
| --------- | -----------------: | ----: | ---------: |
| TASK-1501 |  FIRE 計算エンジン |  1.0d |       5 件 |
| TASK-1502 | シナリオ分析ツール |  1.0d |       4 件 |
| TASK-1503 | パターン分析ツール | 1.25d |       6 件 |
| TASK-1504 |       MCP/API 統合 | 0.75d | API テスト |
| TASK-1505 |      E2E・品質検証 |  1.0d |     15+ 件 |

品質目標: 新規コード 80% 以上、API レスポンス < 1s など

---

### リスクと対策（抜粋）

- 複利計算の精度: テストケースで検証
- シナリオの組合せ爆発: 最大 5 シナリオに制限
- パターン分析のノイズ: 最低 3 か月以上のデータを要求

---

※ このセクションは `design_phase15.md` の内容を `design.md` に統合したものです。

- サーバーは `fastmcp.FastMCP` を利用し、LLM クライアントと標準入出力経由で通信する。
- データソースは `data/` 配下の家計簿 CSV ファイルとSQLiteデータベース（全てローカル）。外部ネットワーク通信は行わない。
- SQLiteは重複検出結果の永続化に使用（data/household.db）。
- 解析ロジックは pandas/numpy によるインメモリ処理で完結する。

### 1.2 コンポーネント構成

| コンポーネント    | 主な責務                            | 主な実装                                             | 対応要件        |
| ----------------- | ----------------------------------- | ---------------------------------------------------- | --------------- |
| MCP Server        | リソース/ツール定義とリクエスト分岐 | `src/server.py`                                      | 全要件          |
| Data Loader       | CSV ファイルの読み込みと前処理      | `src/household_mcp/dataloader.py`                    | FR-001〜FR-003  |
| Trend Analyzer    | 月次指標計算モジュール              | `src/household_mcp/analysis/trends.py`               | FR-001, FR-005  |
| Query Resolver    | 質問パラメータ解釈ユーティリティ    | `src/household_mcp/utils/query_parser.py`            | FR-002, FR-003  |
| Formatter         | 数値書式・テキスト生成              | `src/household_mcp/utils/formatters.py`              | NFR-008         |
| DatabaseManager   | SQLiteセッション管理と初期化        | `src/household_mcp/database/manager.py`              | FR-009, NFR-013 |
| CSVImporter       | CSV→DBインポート処理                | `src/household_mcp/database/csv_importer.py`         | FR-009-3        |
| DuplicateDetector | 重複検出アルゴリズム                | `src/household_mcp/duplicate/detector.py`            | FR-009-1        |
| ChartGenerator    | グラフ画像生成（matplotlib使用）    | `src/household_mcp/visualization/chart_generator.py` | FR-015          |
| ImageStreamer     | 画像ストリーミング配信              | `src/household_mcp/streaming/image_streamer.py`      | FR-016          |
| HTTPServer        | FastAPI HTTPエンドポイント          | `src/household_mcp/http_server.py`                   | FR-016          |
| ChartCache        | 画像キャッシング管理                | `src/household_mcp/streaming/chart_cache.py`         | FR-016, NFR-005 |
| EnhancedTools     | MCPツールの画像生成拡張             | `src/household_mcp/tools/enhanced_tools.py`          | FR-017          |

### 1.3 技術スタック

| 区分         | 採用技術                             | 備考                   |
| ------------ | ------------------------------------ | ---------------------- |
| 言語         | Python 3.12 (uv 管理)                | `pyproject.toml` 参照  |
| MCP 実装     | `fastmcp`                            | 既存コードで使用       |
| データ処理   | pandas, numpy                        | CSV の集計と指標算出   |
| データベース | SQLite (better-sqlite3)              | 重複判定結果の永続化   |
| 可視化       | matplotlib>=3.8.0, plotly>=5.17.0    | グラフ画像生成         |
| 画像処理     | pillow>=10.0.0                       | 画像フォーマット変換   |
| HTTP         | FastAPI>=0.100.0, uvicorn>=0.23.0    | 画像配信エンドポイント |
| キャッシング | cachetools>=5.3.0                    | 画像キャッシュ管理     |
| フォーマット | Python 標準 `locale`, `decimal` など | 数値の桁区切り、丸め   |
| テスト       | pytest, pytest-asyncio               | 単体・統合テスト       |

---

## 2. データ設計

### 2.1 データソース

- **ファイル位置**: `data/収入・支出詳細_YYYY-MM-DD_YYYY-MM-DD.csv`
- **エンコーディング**: `cp932`
- **主要カラム**:
  - `計算対象` (0/1)
  - `金額（円）` (負の値で支出を表す)
  - `大項目` / `大分類`
  - `中項目` / `中分類`
  - `日付`

### 2.2 読み込みフロー

1. `load_csv_from_month(year, month, src_dir="data")` を通じて pandas DataFrame を取得。
2. 引数に応じて対象期間の CSV を結合し、`計算対象 == 1` かつ `金額（円） < 0` の行にフィルタリング。
3. 型定義: 金額は `Int64`、カテゴリ列は pandas Categorical として読み込む。
4. 将来のトレンド分析では、列名の揺れ (`大項目` / `大分類`) を吸収するマッピングを実装する。

### 2.3 データ検証

- 欠損値: カテゴリまたは金額が欠落している行は分析対象から除外。
- 重複: 同一日・同金額・同カテゴリの重複は保持（家計簿の明細として許容）。
- 利用可能月一覧: `get_available_months()` で 2025 年 1〜12 月を提供（現状はハードコーディング、将来自動検出予定）。

### 2.4 SQLiteデータベーススキーマ

重複検出・解決機能のために、以下のSQLiteテーブルを使用する（詳細はセクション12.3を参照）:

- **transactions**: CSV取引データのキャッシュと重複管理フラグ
- **duplicate_checks**: 重複検出履歴とユーザー判定結果

---

## 3. MCP リソース / ツール設計

### 3.1 既存リソース・ツール

| 名称                          | 種別     | 概要                                        | 返却値                 |
| ----------------------------- | -------- | ------------------------------------------- | ---------------------- |
| `data://category_hierarchy`   | Resource | 大項目→中項目の階層辞書                     | `dict[str, list[str]]` |
| `data://household_categories` | Resource | カテゴリ一覧（`category_hierarchy` と同等） | `dict[str, list[str]]` |
| `data://available_months`     | Resource | 利用可能な年月の静的リスト                  | `list[dict]`           |
| `get_monthly_household`       | Tool     | 指定年月の明細一覧                          | `list[dict]`           |

### 3.2 追加予定リソース/ツール（トレンド分析）

| 名称                            | 種別     | 役割                                            | 主な入力パラメータ                             | 対応要件       |
| ------------------------------- | -------- | ----------------------------------------------- | ---------------------------------------------- | -------------- |
| `data://category_trend_summary` | Resource | 直近 12 か月のカテゴリ別指標を返す API          | なし（サーバ内部で最新期間を判定）             | FR-001         |
| `get_category_trend`            | Tool     | 質問に応じたカテゴリ/月範囲のトレンド解説を返す | `category`, `start_month`, `end_month`（任意） | FR-002, FR-003 |

- トレンド計算結果は辞書（カテゴリ × 月）で保持し、ツール側でテキスト整形して返す。
- MCP クライアント（LLM）が自然言語入力を解析し、該当パラメータを渡す想定。パラメータが不足する場合はサーバー側で補完ロジックを適用する。

---

## 4. トレンド分析設計

### 4.1 コンポーネント詳細

- **CategoryTrendAnalyzer** (`analysis/trends.py`, 予定)
  - 直近 12 か月分の CSV を読み込み、カテゴリ別の月次支出を集計。
  - 指標: 金額、前月比、12か月移動平均、前年同月比。
- **MonthCategoryResolver** (`utils/query_parser.py`, 予定)
  - 自然言語で指定された期間やカテゴリを構造化パラメータに変換。
  - 不足時は利用可能月一覧から最新 12 か月をデフォルト適用。
- **TrendResponseFormatter** (`utils/formatters.py`, 予定)
  - 指標値をフォーマットし、自然言語応答テンプレートに埋め込む。

### 4.2 処理手順

```text
1. get_category_trend が {category?, start_month?, end_month?} を受け取る
2. MonthCategoryResolver が対象カテゴリ・期間を確定
3. CategoryTrendAnalyzer が対象月の DataFrame を取得
4. pandas groupby で月次合計を計算し、指標列（前月比/前年比/移動平均）を付与
5. TrendResponseFormatter が指標をテキストに整形
6. MCP ツールの戻り値として LLM に返却
```

### 4.3 指標計算ロジック（擬似コード）

```python
import numpy as np

def compute_metrics(df: pd.DataFrame) -> pd.DataFrame:
    monthly = (
        df.groupby(["年月", "カテゴリ"], as_index=False)["金額"].sum()
          .sort_values(["カテゴリ", "年月"])
    )
    monthly["前月比"] = monthly.groupby("カテゴリ")["金額"].pct_change()
    monthly["移動平均"] = monthly.groupby("カテゴリ")["金額"].transform(
        lambda s: s.rolling(12, min_periods=1).mean()
    )
    monthly["前年比"] = monthly.groupby("カテゴリ")["金額"].pct_change(periods=12)
    return monthly
```

- 指標は `%` に換算して小数第 1 位で丸め、`format_percentage` ユーティリティで整形。
- 前年同月が存在しない場合は `None` を設定し、応答では "N/A" を表示。
- 移動平均はデータ不足時に利用可能な範囲のみで計算。

### 4.4 応答テンプレート例

```text
食費カテゴリの 2025年06月〜2025年07月の推移です。
- 2025年06月: 62,500円
- 2025年07月: 58,300円 （前月比 -6.7%, 前年同月比 +3.2%）
- 12か月平均: 60,480円
```

- カテゴリ未指定の場合は、支出額上位 3 カテゴリを降順で列挙。
- データ不足時は「過去 {n} か月分のデータで計算しました」と注記する。

### 4.5 エラー処理とフォールバック

| ケース                   | 例外                                    | メッセージ方針                       |
| ------------------------ | --------------------------------------- | ------------------------------------ |
| 対象 CSV が見つからない  | `FileNotFoundError` → `DataSourceError` | 「データファイルが見つかりません」   |
| 指定カテゴリが存在しない | `ValidationError`                       | 「該当カテゴリが見つかりません」     |
| データ不足で指標計算不可 | `AnalysisError`                         | 「対象期間のデータが不足しています」 |

---

## 5. エラーハンドリング設計

```python
class HouseholdMCPError(Exception):
    """Base exception for household MCP server"""


class ValidationError(HouseholdMCPError):
    """Invalid user input or unsupported category."""


class DataSourceError(HouseholdMCPError):
    """CSV ファイルの読み込み失敗時に使用。"""


class AnalysisError(HouseholdMCPError):
    """指標計算やデータ前処理でのエラー。"""
```

- MCP ツール/リソース内で例外が発生した場合、メッセージと共に失敗レスポンスを返し、LLM がユーザーに通知できるようにする。

---

## 6. 非機能要件への対応

| 要件                           | 設計対応                                                                                                                                                                                                                                                                                                              |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| NFR-001 (応答表現)             | `format_currency` と `format_percentage` で桁区切り・丸めを統一する。                                                                                                                                                                                                                                                 |
| NFR-002 (パフォーマンス)       | pandas 処理は 12 か月分の明細（数千行想定）を 1 秒以内で完了し、結果を簡易キャッシュに保持する。                                                                                                                                                                                                                      |
| NFR-003 (信頼性)               | 例外クラスを通じて原因別メッセージを返却し、CSV 読み込み時には対象ファイル名をログに記録。                                                                                                                                                                                                                            |
| NFR-004 (セキュリティ)         | 全処理をローカル内で完結させ、ログにも個人情報を残さない。外部通信は行わない。                                                                                                                                                                                                                                        |
| NFR-016 (リポジトリ肥大化対策) | ファイル行数を500行以下に保つ。単一責任原則に従い、機能・責任ごとにモジュール分割。共通ユーティリティ（formatters.py、query_parser.py等）に重複排除。テストも200行以上は分割。定期的なリファクタリング（Phase終了時）で品質保持。REFACTORING.md に実施履歴を記録。                                                    |
| NFR-017 (エディター品質確保)   | Pylance/Ruff の警告ゼロを目指す。全関数・メソッドに型アノテーション完備。複雑な関数・クラスに Docstring（description、params、returns）記載。ruff check・ruff format・Pylance による定期チェック（最低PR前）。CI/CD でコード品質ゲート（テスト・Lint・型チェック）を実装し、リリース前に High/Medium エラーをゼロに。 |

---

## 7. テスト方針

### 7.1 単体テスト

- `tests/unit/test_dataloader.py` — 月/年指定パターンごとの読み込み検証。
- `tests/unit/analysis/test_trends.py` — `compute_metrics` の数値検証（TS-001〜TS-003）。
- `tests/unit/tools/test_get_category_trend.py` — パラメータ別のレスポンス生成テスト（TS-004〜TS-006）。

### 7.2 統合テスト

- `tests/integration/test_trend_pipeline.py` — 12 か月ダミー CSV を用いたエンドツーエンド検証（TS-007〜TS-009）。

### 7.3 品質ゲート

- `uv run pytest tests/unit` を最小スモークとして用意し、主要メトリクスのリグレッションを検知する。

---

## 8. プロジェクト構造（現状 + 追加予定）

```text
my_household_mcpserver/
├── data/
├── src/
│   ├── household_mcp/
│   │   ├── __init__.py
│   │   ├── dataloader.py
│   │   ├── analysis/
│   │   │   ├── __init__.py
│   │   │   └── trends.py        # ★ 新規追加予定
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   └── trend_tool.py    # ★ 新規追加予定
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── formatters.py    # ★ 新規追加予定
│   │       └── query_parser.py  # ★ 新規追加予定
│   └── server.py
├── requirements.md
├── design.md
├── tasks.md
└── ...
```

---

## 11. モノレポ構成設計（FR-020対応）

本セクションでは、フロントエンドとバックエンドを分離しメンテナンス性を向上させるためのモノレポ構成を定義する。対象要件は FR-020、関連NFRは NFR-014（モジュール分離）と NFR-015（DX）。

### 11.1 リポジトリレイアウト（提案）

```text
my_household_mcpserver/
├── backend/                         # Python バックエンド（MCP/HTTP API/分析）
│   ├── pyproject.toml               # ルートから移設（uv/依存/extras定義）
│   ├── src/
│   │   └── household_mcp/          # 既存の Python パッケージをそのまま移動
│   ├── tests/                       # 既存の Python テスト一式を移動
│   ├── scripts/                     # バックエンド専用の補助スクリプト
│   └── README.md                    # バックエンド固有の利用/開発ガイド
├── frontend/                        # Web フロントエンド（静的サイト）
│   ├── index.html
│   ├── duplicates.html
│   ├── css/
│   ├── js/
│   └── README.md                    # フロントエンド固有の利用/開発ガイド
├── shared/                          # 共有（将来、当面は空で可）
├── data/                            # データはリポジトリ直下に維持（後方互換）
├── docs/                            # 全体ドキュメント（パス更新のみ）
├── README.md                        # リポジトリ全体のトップREADME
├── Makefile                         # ルートタスクの委譲（backend/frontendへ）
└── .github/                         # CI（パス更新、backend をワークディレクトリに）
```

注記:

- 既存の `src/`, `tests/` はそれぞれ `backend/src`, `backend/tests` へ移設。
- `data/` はルートに残し、バックエンドからは相対パス `../data` で参照（設定で上書き可能）。
- 共有スキーマや定数が将来必要になれば `shared/` を活用。

### 11.2 タスク/コマンドの統一方針（DX）

- ルート実行（開発者体験の統一）
- フォーマット: `uv -C backend run black .`
- インポート整形: `uv -C backend run isort .`
- Lint: `uv -C backend run flake8`
- 型: `uv -C backend run mypy src/`
- セキュリティ: `uv -C backend run bandit -r src/`
- テスト: `uv -C backend run pytest`

- サーバ起動（開発）
- API: `uv -C backend run uvicorn household_mcp.web.http_server:create_http_app --factory --reload --host 0.0.0.0 --port 8000`
- Web: `python3 -m http.server 8080`（cwd=frontend/）
- VS Code の既存タスクはルートから backend/frontend へ委譲（`options.cwd` または `-C` を使用）。

### 11.3 CORS/ポート設計

- バックエンド: `http://localhost:8000`
- フロントエンド: `http://localhost:8080`
- CORS: FastAPI の `CORSMiddleware` で `allow_origins=["http://localhost:8080"]` を基本とし、開発時のみ `*` を許可可能。

### 11.4 移行計画（ファイル移動マッピング）

| 旧パス                     | 新パス                                  |
| -------------------------- | --------------------------------------- |
| `src/`                     | `backend/src/`                          |
| `tests/`                   | `backend/tests/`                        |
| `frontend/`                | `frontend/`                             |
| `pyproject.toml`           | `backend/pyproject.toml`                |
| `scripts/`（Python系のみ） | `backend/scripts/` へ、汎用はルート維持 |
| `README.md`（ルート）      | ルートに維持（内容更新）                |
| `docs/`                    | ルートに維持（リンク更新）              |

注意点:

- Python パッケージルートが `backend/src` に変わるため、mypy/pytest/path などの参照を更新。
- VS Code タスク（All Checks / Start HTTP API など）は `backend/` と `frontend/` に対応させる。

### 11.5 リスク/ロールバック

- 影響範囲が広いため、移行は以下の順でコミットを分割：
    1) ディレクトリ作成 + README 追加（空の器）
    2) フロントエンド移設（`frontend/` 構造化）
    3) バックエンド移設（`src/`, `tests/`, `pyproject.toml` → `backend/`）
    4) タスク/スクリプト/CI の参照更新
    5) ドキュメントパス修正
- 各ステップで `All Checks` を実行してグリーンを確認。問題があれば直前コミットへロールバック可能。

### 11.6 受け入れ基準との対応

- TS-017: ルートに `backend/` と `frontend/` が存在し、それぞれ README がある
- TS-018: ルートの All Checks がグリーン（backend を対象として実行）
- TS-019: `backend/` で `uv run pytest` が成功、API サーバ起動可能
- TS-020: `frontend/` で `python -m http.server 8080` により主要ページが表示

---

## 9. 画像生成・ストリーミング機能設計

### 10.1 アーキテクチャ拡張

要件 FR-004〜FR-006 に対応するため、既存アーキテクチャに以下のコンポーネントを追加する：

```text
┌──────────────┐   MCPプロトコル   ┌─────────────────────┐
│  LLMクライアント │ ◄─────────────► │ 家計簿分析 MCP サーバ │
└──────────────┘                  └────────┬────────────┘
                                                │
                                                ├─ pandas DataFrame
                                                │
                          HTTP Streaming     ├─ Chart Generator ──┐
                      ◄──────────────────────┤                      │
                                                │                      ▼
                                                │              ┌────────────┐
                                                │              │ Image Buffer │
                                                └──────────────┘
                                      ┌────────────────────────┐
                                      │  CSV データ / ローカルFS │
                                      └────────────────────────┘
```

### 10.2 新規コンポーネント

| コンポーネント  | 主な責務                                | 実装ファイル                                         | 対応要件 |
| --------------- | --------------------------------------- | ---------------------------------------------------- | -------- |
| Chart Generator | matplotlib/plotlyによるグラフ画像生成   | `src/household_mcp/visualization/chart_generator.py` | FR-004   |
| Image Streamer  | HTTPストリーミングによる画像配信        | `src/household_mcp/streaming/image_streamer.py`      | FR-005   |
| Tool Extensions | 既存MCPツールの引数拡張とルーティング   | `src/household_mcp/tools/enhanced_tools.py`          | FR-006   |
| HTTP Server     | FastAPI/uvicornによるHTTPエンドポイント | `src/household_mcp/server/http_server.py`            | FR-005   |

### 10.3 技術スタック拡張

| 区分             | 追加技術        | 用途                          | 備考                 |
| ---------------- | --------------- | ----------------------------- | -------------------- |
| 画像生成         | matplotlib 3.8+ | グラフ描画ライブラリ          | 日本語フォント対応   |
| 画像生成         | pillow 10.0+    | 画像処理・形式変換            | PNG/JPEG出力         |
| HTTP Server      | FastAPI 0.100+  | RESTful API・ストリーミング   | 非同期処理対応       |
| HTTP Server      | uvicorn 0.23+   | ASGI アプリケーションサーバー | 開発・本番両用       |
| 画像フォーマット | io.BytesIO      | メモリ内画像データ処理        | Python標準ライブラリ |

### 10.4 MCPツール拡張設計

#### 10.4.1 引数拡張仕様

既存ツール `get_monthly_household` と `get_category_trend` を以下のように拡張：

```python
@dataclass
class ToolParameters:
    # 既存引数（後方互換性維持）
    year: int
    month: int
    category: Optional[str] = None

    # 新規引数
    output_format: Literal["text", "image"] = "text"
    graph_type: Optional[Literal["bar", "line", "pie", "area"]] = None
    image_size: str = "800x600"
    image_format: Literal["png", "svg"] = "png"
```

#### 10.4.2 ルーティング設計

```python
def enhanced_get_monthly_household(**params) -> Union[str, dict]:
    if params.get("output_format") == "image":
        # 画像生成パスへ分岐
        chart_data = prepare_chart_data(**params)
        image_url = generate_and_stream_chart(chart_data, **params)
        return {
            "type": "image",
            "url": image_url,
            "alt_text": f"家計簿グラフ - {params['year']}年{params['month']}月"
        }
    else:
        # 従来のテキスト出力
        return generate_text_response(**params)
```

### 10.5 画像生成設計

#### 10.5.1 ChartGenerator クラス

```python
class ChartGenerator:
    def __init__(self, font_path: Optional[str] = None):
        self.font_path = font_path or self._detect_japanese_font()

    def create_monthly_pie_chart(self, data: pd.DataFrame, **options) -> BytesIO:
        """月次支出の円グラフ生成"""

    def create_category_trend_line(self, data: pd.DataFrame, **options) -> BytesIO:
        """カテゴリ別推移の線グラフ生成"""

    def create_comparison_bar_chart(self, data: pd.DataFrame, **options) -> BytesIO:
        """比較棒グラフ生成"""
```

#### 10.5.2 グラフタイプ別設計

| グラフタイプ | 適用ツール              | データ構造         | 実装方針                         |
| ------------ | ----------------------- | ------------------ | -------------------------------- |
| `pie`        | `get_monthly_household` | カテゴリ別支出金額 | matplotlib.pyplot.pie()          |
| `bar`        | `get_monthly_household` | カテゴリ別支出金額 | matplotlib.pyplot.bar()          |
| `line`       | `get_category_trend`    | 月次推移データ     | matplotlib.pyplot.plot()         |
| `area`       | `get_category_trend`    | 月次推移データ     | matplotlib.pyplot.fill_between() |

#### 10.5.3 日本語フォント対応

```python
def _detect_japanese_font(self) -> str:
    """システム内の日本語フォントを自動検出"""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
        "/System/Library/Fonts/Hiragino Sans GB.ttc",      # macOS  
        "C:/Windows/Fonts/msgothic.ttc",                   # Windows
    ]
    for font_path in candidates:
        if os.path.exists(font_path):
            return font_path
    return None  # システムデフォルトを使用
```

### 10.6 HTTPストリーミング設計

#### 10.6.1 FastAPI エンドポイント

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

@app.get("/api/charts/{chart_id}")
async def stream_chart(chart_id: str):
    """生成済み画像のストリーミング配信"""
    image_buffer = chart_cache.get(chart_id)
    if not image_buffer:
        raise HTTPException(404, "Chart not found")

    return StreamingResponse(
        io.BytesIO(image_buffer),
        media_type="image/png",
        headers={"Content-Disposition": f"inline; filename=chart_{chart_id}.png"}
    )
```

#### 10.6.2 チャンクストリーミング

```python
async def stream_image_chunks(image_data: bytes, chunk_size: int = 8192):
    """画像データを分割してストリーミング"""
    for i in range(0, len(image_data), chunk_size):
        chunk = image_data[i:i + chunk_size]
        yield chunk
        await asyncio.sleep(0.01)  # CPU負荷軽減
```

#### 10.6.3 キャッシュ戦略

```python
from cachetools import TTLCache
import hashlib

class ChartCache:
    def __init__(self, max_size: int = 50, ttl: int = 3600):
        self.cache = TTLCache(maxsize=max_size, ttl=ttl)

    def get_key(self, params: dict) -> str:
        """パラメータからキャッシュキーを生成"""
        key_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, key: str) -> Optional[bytes]:
        return self.cache.get(key)

    def set(self, key: str, image_data: bytes):
        self.cache[key] = image_data
```

### 10.7 統合フロー設計

#### 10.7.1 画像生成・配信フロー

```text
1. MCPクライアント → get_monthly_household(output_format="image")
2. Enhanced Tool → データ取得・前処理
3. ChartGenerator → matplotlib でグラフ生成
4. ChartCache → 生成画像をメモリキャッシュ
5. HTTP Server → ユニークURLを生成・返却
6. MCPクライアント → 返却されたURLにHTTPリクエスト
7. Image Streamer → キャッシュから画像を取得・ストリーミング配信
```

#### 10.7.2 エラーハンドリング拡張

```python
class ChartGenerationError(HouseholdMCPError):
    """グラフ生成時のエラー"""

class StreamingError(HouseholdMCPError):
    """HTTPストリーミング時のエラー"""

# フォールバック処理
def safe_generate_chart(data, **params):
    try:
        return generate_chart(data, **params)
    except ChartGenerationError:
        # テキスト形式にフォールバック
        return generate_text_response(data, **params)
```

### 10.8 非機能要件対応

#### 10.8.1 パフォーマンス対応（NFR-005, NFR-006）

| 要件            | 実装方針                                      |
| --------------- | --------------------------------------------- |
| 画像生成3秒以内 | matplotlib の描画設定最適化、データサイズ制限 |
| メモリ50MB以下  | 生成後の即座開放、BytesIO使用                 |
| 転送1MB/秒以上  | 非同期ストリーミング、適切なチャンクサイズ    |
| 同時接続5件     | FastAPI の並行処理、コネクションプール        |

#### 10.8.2 画像品質対応（NFR-007）

```python
# matplotlib 設定
plt.rcParams.update({
    'font.size': 12,
    'axes.titlesize': 16,
    'axes.labelsize': 14,
    'figure.figsize': (10, 6),
    'figure.dpi': 100,
    'savefig.dpi': 150,
    'savefig.bbox': 'tight'
})

# 配色パレット
CATEGORY_COLORS = [
    '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
    '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F'
]
```

### 10.9 プロジェクト構造拡張

```text
my_household_mcpserver/
├── src/
│   ├── household_mcp/
│   │   ├── visualization/
│   │   │   ├── __init__.py
│   │   │   ├── chart_generator.py    # ★ 新規
│   │   │   └── styles.py             # ★ 新規
│   │   ├── streaming/
│   │   │   ├── __init__.py
│   │   │   ├── image_streamer.py     # ★ 新規
│   │   │   └── cache.py              # ★ 新規
│   │   ├── server/
│   │   │   ├── __init__.py
│   │   │   └── http_server.py        # ★ 新規
│   │   └── tools/
│   │       └── enhanced_tools.py     # ★ 新規
├── fonts/                            # ★ 新規
│   └── NotoSansCJK-Regular.ttc
└── tests/
    ├── unit/
    │   ├── test_chart_generator.py   # ★ 新規
    │   └── test_image_streamer.py    # ★ 新規
    └── integration/
        └── test_streaming_pipeline.py # ★ 新規
```

### 10.10 設定・環境変数

```python
# src/household_mcp/config.py
@dataclass
class StreamingConfig:
    http_host: str = "localhost"
    http_port: int = 8080
    chart_cache_size: int = 50
    chart_cache_ttl: int = 3600
    chunk_size: int = 8192
    max_image_size: str = "1920x1080"
    default_image_format: str = "png"
    font_path: Optional[str] = None
```

---

## 10. 重複検出・解決機能設計（FR-009対応）

### 10.1 アーキテクチャ拡張

要件 FR-009-1〜FR-009-4 に対応するため、既存アーキテクチャに以下のコンポーネントを追加する：

```text
┌──────────────┐   MCPプロトコル   ┌─────────────────────────┐
│  LLMクライアント │ ◄─────────────► │  家計簿分析 MCP サーバ   │
└──────────────┘                  └────────┬────────────────┘
                                                │
                                                ├─ Duplicate Detector
                                                │  (重複検出エンジン)
                                                │
                                                ├─ User Confirmation
                                                │  (MCPツール経由)
                                                │
                                                ▼
                                      ┌─────────────────────┐
                                      │   SQLite Database   │
                                      │  (data/household.db)│
                                      │                     │
                                      │ - transactions      │
                                      │ - duplicate_checks  │
                                      └─────────────────────┘
                                                ▲
                                                │ CSV読み込み時にキャッシュ
                                                │
                                      ┌────────────────────────┐
                                      │  CSV データ / ローカルFS │
                                      └────────────────────────┘
```

### 10.2 新規コンポーネント

| コンポーネント       | 主な責務                         | 実装ファイル                                 | 対応要件 |
| -------------------- | -------------------------------- | -------------------------------------------- | -------- |
| Database Manager     | SQLiteのスキーマ管理とCRUD操作   | `src/household_mcp/database/db_manager.py`   | FR-009-3 |
| CSV to DB Importer   | CSVデータのDB取り込み            | `src/household_mcp/database/csv_importer.py` | FR-009-3 |
| Duplicate Detector   | 重複候補の検出ロジック           | `src/household_mcp/duplicate/detector.py`    | FR-009-1 |
| Duplicate Comparator | 誤差許容を含む比較ロジック       | `src/household_mcp/duplicate/comparator.py`  | FR-009-1 |
| Duplicate Tools      | ユーザー確認用MCPツール群        | `src/household_mcp/tools/duplicate_tools.py` | FR-009-2 |
| Duplicate Resolver   | 重複解消処理（フラグ設定・復元） | `src/household_mcp/duplicate/resolver.py`    | FR-009-4 |

### 10.3 技術スタック拡張

| 区分         | 追加技術        | 用途                           | 備考                   |
| ------------ | --------------- | ------------------------------ | ---------------------- |
| データベース | SQLite 3.x      | ローカルデータベース           | Python標準ライブラリ   |
| ORM/DB操作   | SQLAlchemy      | データベース抽象化レイヤー     | 2.0以降を推奨          |
| 日付処理     | python-dateutil | 日付誤差計算                   | 標準ライブラリで代替可 |
| 文字列類似度 | difflib         | 摘要の類似度計算（将来拡張用） | Python標準ライブラリ   |

### 10.4 データベース設計

#### 12.4.1 スキーマ定義

**transactions テーブル** - 取引データのキャッシュ

```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- 元データ
    source_file TEXT NOT NULL,              -- 元のCSVファイル名
    row_number INTEGER NOT NULL,            -- CSV内の行番号
    date DATE NOT NULL,                     -- 取引日付
    amount DECIMAL(12, 2) NOT NULL,         -- 金額（円）
    description TEXT,                       -- 摘要
    category_major TEXT,                    -- 大項目
    category_minor TEXT,                    -- 中項目
    account TEXT,                           -- 口座
    memo TEXT,                              -- メモ
    is_target INTEGER DEFAULT 1,            -- 計算対象フラグ

    -- 重複管理フィールド
    is_duplicate INTEGER DEFAULT 0,         -- 重複フラグ（0=非重複, 1=重複）
    duplicate_of INTEGER,                   -- 参照先取引ID
    duplicate_checked INTEGER DEFAULT 0,    -- ユーザー確認済みフラグ
    duplicate_checked_at TIMESTAMP,         -- 確認日時

    -- メタ情報
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- インデックス用複合キー
    UNIQUE(source_file, row_number),
    FOREIGN KEY(duplicate_of) REFERENCES transactions(id)
);

-- パフォーマンス最適化用インデックス
CREATE INDEX idx_date_amount ON transactions(date, amount);
CREATE INDEX idx_is_duplicate ON transactions(is_duplicate);
CREATE INDEX idx_duplicate_of ON transactions(duplicate_of);
CREATE INDEX idx_date_range ON transactions(date);
```

**duplicate_checks テーブル** - 重複検出の履歴

```sql
CREATE TABLE duplicate_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    transaction_id_1 INTEGER NOT NULL,      -- 取引ID1
    transaction_id_2 INTEGER NOT NULL,      -- 取引ID2

    -- 検出パラメータ
    detection_date_tolerance INTEGER,       -- 日付誤差(日数)
    detection_amount_tolerance_abs DECIMAL(12, 2),  -- 金額絶対誤差(円)
    detection_amount_tolerance_pct DECIMAL(5, 2),   -- 金額割合誤差(%)

    -- 検出結果
    similarity_score DECIMAL(5, 4),         -- 類似度スコア (0.0-1.0)
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- ユーザー判定
    user_decision TEXT,                     -- 'duplicate' / 'not_duplicate' / 'skip'
    decided_at TIMESTAMP,

    FOREIGN KEY(transaction_id_1) REFERENCES transactions(id),
    FOREIGN KEY(transaction_id_2) REFERENCES transactions(id),
    UNIQUE(transaction_id_1, transaction_id_2)
);

CREATE INDEX idx_decision ON duplicate_checks(user_decision);
```

#### 12.4.2 SQLAlchemy モデル定義

```python
from sqlalchemy import Column, Integer, String, Decimal, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 元データ
    source_file = Column(String(255), nullable=False)
    row_number = Column(Integer, nullable=False)
    date = Column(DateTime, nullable=False, index=True)
    amount = Column(Decimal(12, 2), nullable=False)
    description = Column(Text)
    category_major = Column(String(100))
    category_minor = Column(String(100))
    account = Column(String(100))
    memo = Column(Text)
    is_target = Column(Integer, default=1)

    # 重複管理
    is_duplicate = Column(Integer, default=0, index=True)
    duplicate_of = Column(Integer, ForeignKey('transactions.id'))
    duplicate_checked = Column(Integer, default=0)
    duplicate_checked_at = Column(DateTime)

    # メタ情報
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # リレーション
    original_transaction = relationship('Transaction', remote_side=[id], backref='duplicates')
    duplicate_checks_as_1 = relationship('DuplicateCheck', foreign_keys='DuplicateCheck.transaction_id_1')
    duplicate_checks_as_2 = relationship('DuplicateCheck', foreign_keys='DuplicateCheck.transaction_id_2')


class DuplicateCheck(Base):
    __tablename__ = 'duplicate_checks'

    id = Column(Integer, primary_key=True, autoincrement=True)

    transaction_id_1 = Column(Integer, ForeignKey('transactions.id'), nullable=False)
    transaction_id_2 = Column(Integer, ForeignKey('transactions.id'), nullable=False)

    # 検出パラメータ
    detection_date_tolerance = Column(Integer)
    detection_amount_tolerance_abs = Column(Decimal(12, 2))
    detection_amount_tolerance_pct = Column(Decimal(5, 2))

    # 検出結果
    similarity_score = Column(Decimal(5, 4))
    detected_at = Column(DateTime, default=datetime.now)

    # ユーザー判定
    user_decision = Column(String(20))  # 'duplicate', 'not_duplicate', 'skip'
    decided_at = Column(DateTime)

    # リレーション
    transaction_1 = relationship('Transaction', foreign_keys=[transaction_id_1])
    transaction_2 = relationship('Transaction', foreign_keys=[transaction_id_2])
```

### 10.5 重複検出ロジック設計

#### 12.5.1 DuplicateDetector クラス

```python
from dataclasses import dataclass
from typing import List, Tuple
from datetime import timedelta

@dataclass
class DetectionOptions:
    """重複検出オプション"""
    date_tolerance_days: int = 0           # 日付誤差許容(±日数)
    amount_tolerance_abs: float = 0.0      # 金額絶対誤差(±円)
    amount_tolerance_pct: float = 0.0      # 金額割合誤差(±%)
    min_similarity_score: float = 0.8      # 最小類似度スコア


class DuplicateDetector:
    """重複検出エンジン"""

    def __init__(self, db_session, options: DetectionOptions = None):
        self.db = db_session
        self.options = options or DetectionOptions()

    def detect_duplicates(
        self,
        transaction_ids: List[int] = None
    ) -> List[Tuple[Transaction, Transaction, float]]:
        """
        重複候補を検出

        Args:
            transaction_ids: 検出対象の取引IDリスト。Noneの場合は全件検索

        Returns:
            (取引1, 取引2, 類似度スコア) のリスト
        """
        candidates = []

        # 検出対象の取得（is_duplicate=0 のみ）
        query = self.db.query(Transaction).filter(
            Transaction.is_duplicate == 0
        )
        if transaction_ids:
            query = query.filter(Transaction.id.in_(transaction_ids))

        transactions = query.all()

        # 全ペアの比較（効率化のため日付でグルーピング）
        grouped = self._group_by_date_range(transactions)

        for date_group in grouped.values():
            for i, trans1 in enumerate(date_group):
                for trans2 in date_group[i+1:]:
                    if self._is_potential_duplicate(trans1, trans2):
                        score = self._calculate_similarity(trans1, trans2)
                        if score >= self.options.min_similarity_score:
                            candidates.append((trans1, trans2, score))

        # スコア降順でソート
        candidates.sort(key=lambda x: x[2], reverse=True)
        return candidates

    def _group_by_date_range(
        self,
        transactions: List[Transaction]
    ) -> dict:
        """日付範囲でグルーピング（効率化）"""
        groups = {}
        tolerance = self.options.date_tolerance_days

        for trans in transactions:
            # 日付を週単位などでグルーピング
            key = trans.date.date().isocalendar()[:2]  # (year, week)
            if key not in groups:
                groups[key] = []
            groups[key].append(trans)

        return groups

    def _is_potential_duplicate(
        self,
        trans1: Transaction,
        trans2: Transaction
    ) -> bool:
        """基本条件チェック（高速フィルタリング）"""
        # 日付チェック
        date_diff = abs((trans1.date - trans2.date).days)
        if date_diff > self.options.date_tolerance_days:
            return False

        # 金額チェック（絶対値）
        if self.options.amount_tolerance_abs > 0:
            amount_diff_abs = abs(float(trans1.amount) - float(trans2.amount))
            if amount_diff_abs > self.options.amount_tolerance_abs:
                return False

        # 金額チェック（割合）
        if self.options.amount_tolerance_pct > 0:
            avg_amount = (abs(float(trans1.amount)) + abs(float(trans2.amount))) / 2
            if avg_amount > 0:
                amount_diff_pct = abs(float(trans1.amount) - float(trans2.amount)) / avg_amount * 100
                if amount_diff_pct > self.options.amount_tolerance_pct:
                    return False
        else:
            # 誤差許容なしの場合は完全一致のみ
            if trans1.amount != trans2.amount:
                return False

        return True

    def _calculate_similarity(
        self,
        trans1: Transaction,
        trans2: Transaction
    ) -> float:
        """類似度スコア計算 (0.0-1.0)"""
        score = 0.0
        weights = []

        # 日付の類似度
        date_diff = abs((trans1.date - trans2.date).days)
        max_diff = max(self.options.date_tolerance_days, 1)
        date_sim = 1.0 - (date_diff / max_diff)
        score += date_sim * 0.4
        weights.append(0.4)

        # 金額の類似度
        amount1 = abs(float(trans1.amount))
        amount2 = abs(float(trans2.amount))
        max_amount = max(amount1, amount2)
        if max_amount > 0:
            amount_sim = 1.0 - abs(amount1 - amount2) / max_amount
        else:
            amount_sim = 1.0
        score += amount_sim * 0.6
        weights.append(0.6)

        return score
```

#### 12.5.2 処理フロー

```text
1. CSV読み込み時
   └─> CSVImporter.import_csv()
       ├─> DBにトランザクション登録（重複チェックなし）
       └─> 登録完了

2. 重複検出実行（手動またはスケジュール）
   └─> DuplicateDetector.detect_duplicates()
       ├─> 未チェック取引を取得
       ├─> 日付・金額条件で候補ペア抽出
       ├─> 類似度スコア計算
       └─> duplicate_checks テーブルに記録

3. ユーザー確認（MCPツール経由）
   └─> list_duplicate_candidates() ツール
       ├─> 候補ペアの詳細を取得
       ├─> LLMクライアントに整形して提示
       └─> ユーザー判定を待機

   └─> confirm_duplicate() ツール
       ├─> ユーザー判定を受信
       ├─> duplicate_checks テーブル更新
       ├─> is_duplicate フラグ設定（decision='duplicate'の場合）
       └─> 処理完了

4. 集計・分析時
   └─> データ取得クエリ
       └─> WHERE is_duplicate = 0 でフィルタ
```

### 10.6 MCPツール設計

#### 12.6.1 ツール一覧

```python
# src/household_mcp/tools/duplicate_tools.py

@mcp.tool()
def detect_duplicates(
    date_tolerance_days: int = 0,
    amount_tolerance_abs: float = 0.0,
    amount_tolerance_pct: float = 0.0,
    transaction_ids: list[int] | None = None
) -> dict:
    """
    重複候補を検出

    Args:
        date_tolerance_days: 日付の誤差許容(±日数)
        amount_tolerance_abs: 金額の絶対誤差許容(±円)
        amount_tolerance_pct: 金額の割合誤差許容(±%)
        transaction_ids: 検出対象の取引IDリスト（省略時は全件）

    Returns:
        {
            "candidates_count": 候補数,
            "message": "5件の重複候補が見つかりました"
        }
    """


@mcp.tool()
def list_duplicate_candidates(
    limit: int = 10,
    skip_checked: bool = True
) -> dict:
    """
    重複候補の一覧を取得

    Args:
        limit: 取得件数上限
        skip_checked: 確認済みをスキップするか

    Returns:
        {
            "candidates": [
                {
                    "check_id": 1,
                    "transaction_1": {...},
                    "transaction_2": {...},
                    "similarity_score": 0.95,
                    "date_diff_days": 0,
                    "amount_diff": 0.0
                },
                ...
            ]
        }
    """


@mcp.tool()
def get_duplicate_candidate_detail(check_id: int) -> dict:
    """
    重複候補の詳細を取得

    Args:
        check_id: duplicate_checks テーブルのID

    Returns:
        {
            "check_id": 1,
            "transaction_1": {
                "id": 100,
                "date": "2024-01-15",
                "amount": -5000,
                "description": "スーパーマーケット A店",
                "category_major": "食費",
                "category_minor": "食料品",
                "source_file": "収入・支出詳細_2024-01-01_2024-01-31.csv",
                "row_number": 45
            },
            "transaction_2": {
                "id": 105,
                "date": "2024-01-15",
                "amount": -5000,
                "description": "スーパーマーケット A店",
                "category_major": "食費",
                "category_minor": "食料品",
                "source_file": "収入・支出詳細_2024-01-01_2024-01-31.csv",
                "row_number": 50
            },
            "similarity_score": 1.0,
            "detection_params": {
                "date_tolerance_days": 0,
                "amount_tolerance_abs": 0.0,
                "amount_tolerance_pct": 0.0
            }
        }
    """


@mcp.tool()
def confirm_duplicate(
    check_id: int,
    decision: Literal["duplicate", "not_duplicate", "skip"]
) -> dict:
    """
    重複判定結果を記録

    Args:
        check_id: duplicate_checks テーブルのID
        decision: ユーザー判定
            - "duplicate": 重複である
            - "not_duplicate": 重複ではない
            - "skip": 保留（後で判断）

    Returns:
        {
            "success": true,
            "message": "重複として記録しました。取引ID 105 にフラグが設定されました。",
            "marked_transaction_id": 105
        }
    """


@mcp.tool()
def restore_duplicate(transaction_id: int) -> dict:
    """
    誤って重複とマークした取引を復元

    Args:
        transaction_id: 復元する取引ID

    Returns:
        {
            "success": true,
            "message": "取引ID 105 を復元しました。"
        }
    """


@mcp.tool()
def get_duplicate_stats() -> dict:
    """
    重複検出の統計情報を取得

    Returns:
        {
            "total_transactions": 10000,
            "marked_duplicates": 25,
            "pending_checks": 5,
            "confirmed_not_duplicate": 3,
            "duplicate_rate": 0.25
        }
    """
```

#### 12.6.2 ユーザー対話フロー例

```text
ユーザー: 「重複している取引があるか確認したい」

AI: detect_duplicates() を実行
    → "5件の重複候補が見つかりました"

AI: list_duplicate_candidates() を実行
    → 候補一覧を取得

AI: ユーザーに提示
    「以下の重複候補が見つかりました:
     1. 2024-01-15 スーパーマーケット -5,000円 (類似度: 100%)
        - 取引ID 100 (行45) と 取引ID 105 (行50)
     2. ...」

ユーザー: 「1番目は重複です。2番目は別の買い物です。」

AI: confirm_duplicate(check_id=1, decision="duplicate")
    confirm_duplicate(check_id=2, decision="not_duplicate")
    → 判定を記録

AI: 「取引ID 105 を重複としてマークしました。
     今後の集計から除外されます。」
```

### 10.7 CSV to DB インポート設計

#### 12.7.1 CSVImporter クラス

```python
class CSVImporter:
    """CSV → DB インポータ"""

    def __init__(self, db_session):
        self.db = db_session

    def import_csv(self, csv_path: str, encoding: str = "cp932") -> dict:
        """
        CSVファイルをDBにインポート

        Args:
            csv_path: CSVファイルパス
            encoding: エンコーディング

        Returns:
            {
                "imported": 件数,
                "skipped": 件数,
                "errors": エラー情報リスト
            }
        """
        df = pd.read_csv(csv_path, encoding=encoding)

        imported = 0
        skipped = 0
        errors = []

        source_file = os.path.basename(csv_path)

        for idx, row in df.iterrows():
            try:
                # 既存チェック（source_file + row_number）
                existing = self.db.query(Transaction).filter(
                    Transaction.source_file == source_file,
                    Transaction.row_number == idx
                ).first()

                if existing:
                    skipped += 1
                    continue

                # 新規登録
                trans = Transaction(
                    source_file=source_file,
                    row_number=idx,
                    date=pd.to_datetime(row['日付']),
                    amount=Decimal(str(row['金額(円)'])),
                    description=row.get('内容', ''),
                    category_major=row.get('大項目', row.get('大分類', '')),
                    category_minor=row.get('中項目', row.get('中分類', '')),
                    account=row.get('口座', ''),
                    memo=row.get('メモ', ''),
                    is_target=int(row.get('計算対象', 1))
                )

                self.db.add(trans)
                imported += 1

            except Exception as e:
                errors.append({
                    "row": idx,
                    "error": str(e)
                })

        self.db.commit()

        return {
            "imported": imported,
            "skipped": skipped,
            "errors": errors
        }

    def import_all_csvs(self, data_dir: str = "data") -> dict:
        """dataディレクトリ内の全CSVをインポート"""
        csv_files = glob.glob(os.path.join(data_dir, "収入・支出詳細_*.csv"))

        total_imported = 0
        total_skipped = 0
        all_errors = []

        for csv_file in sorted(csv_files):
            result = self.import_csv(csv_file)
            total_imported += result["imported"]
            total_skipped += result["skipped"]
            all_errors.extend(result["errors"])

        return {
            "files_processed": len(csv_files),
            "total_imported": total_imported,
            "total_skipped": total_skipped,
            "errors": all_errors
        }
```

### 10.8 非機能要件対応

#### 12.8.1 パフォーマンス最適化（NFR-002）

```python
# インデックス活用
# - (date, amount) 複合インデックス
# - is_duplicate 単独インデックス

# クエリ最適化例
def get_active_transactions(start_date, end_date):
    """集計対象取引の取得（重複除外）"""
    return db.query(Transaction).filter(
        Transaction.is_duplicate == 0,
        Transaction.date.between(start_date, end_date)
    ).all()

# バッチ処理
def detect_duplicates_batch(batch_size=1000):
    """大量データの重複検出（バッチ処理）"""
    offset = 0
    while True:
        batch = db.query(Transaction).filter(
            Transaction.is_duplicate == 0,
            Transaction.duplicate_checked == 0
        ).limit(batch_size).offset(offset).all()

        if not batch:
            break

        detector.detect_duplicates_for_batch(batch)
        offset += batch_size
```

#### 12.8.2 データ整合性保証（NFR-010）

```python
# トランザクション処理
def confirm_duplicate_with_transaction(check_id, decision):
    """原子性を保証した重複確認処理"""
    try:
        with db.begin():  # トランザクション開始
            # 1. duplicate_checks 更新
            check = db.query(DuplicateCheck).filter(
                DuplicateCheck.id == check_id
            ).with_for_update().first()

            check.user_decision = decision
            check.decided_at = datetime.now()

            # 2. transaction フラグ更新（decision='duplicate'の場合）
            if decision == 'duplicate':
                trans2 = db.query(Transaction).filter(
                    Transaction.id == check.transaction_id_2
                ).with_for_update().first()

                trans2.is_duplicate = 1
                trans2.duplicate_of = check.transaction_id_1
                trans2.duplicate_checked = 1
                trans2.duplicate_checked_at = datetime.now()

            db.commit()
            return {"success": True}

    except Exception as e:
        db.rollback()
        raise DuplicateResolutionError(f"重複確認処理に失敗: {e}")
```

### 10.9 エラーハンドリング拡張

```python
class DuplicateDetectionError(HouseholdMCPError):
    """重複検出時のエラー"""

class DuplicateResolutionError(HouseholdMCPError):
    """重複解消処理時のエラー"""

class DatabaseError(HouseholdMCPError):
    """データベース操作のエラー"""

# エラーメッセージの日本語化（NFR-014）
ERROR_MESSAGES = {
    "duplicate_not_found": "指定された重複候補が見つかりません",
    "transaction_not_found": "指定された取引が見つかりません",
    "already_marked": "この取引は既に重複としてマークされています",
    "invalid_decision": "判定値が不正です（duplicate/not_duplicate/skipのいずれか）",
    "db_connection_failed": "データベース接続に失敗しました",
}
```

### 10.10 プロジェクト構造拡張

```text
my_household_mcpserver/
├── data/
│   └── household.db              # ★ 新規（自動生成）
├── src/
│   ├── household_mcp/
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── db_manager.py     # ★ 新規
│   │   │   ├── models.py         # ★ 新規（SQLAlchemyモデル）
│   │   │   └── csv_importer.py   # ★ 新規
│   │   ├── duplicate/
│   │   │   ├── __init__.py
│   │   │   ├── detector.py       # ★ 新規
│   │   │   ├── comparator.py     # ★ 新規
│   │   │   └── resolver.py       # ★ 新規
│   │   ├── tools/
│   │       └── duplicate_tools.py # ★ 新規
└── tests/
    ├── unit/
    │   ├── test_duplicate_detector.py  # ★ 新規
    │   ├── test_csv_importer.py        # ★ 新規
    │   └── test_duplicate_tools.py     # ★ 新規
    └── integration/
        └── test_duplicate_pipeline.py  # ★ 新規
```

### 10.11 設定・環境変数

```python
# src/household_mcp/config.py

@dataclass
class DatabaseConfig:
    db_path: str = "data/household.db"
    echo_sql: bool = False              # SQLログ出力
    pool_size: int = 5
    max_overflow: int = 10

@dataclass
class DuplicateDetectionConfig:
    default_date_tolerance: int = 0
    default_amount_tolerance_abs: float = 0.0
    default_amount_tolerance_pct: float = 0.0
    min_similarity_score: float = 0.8
    batch_size: int = 1000
    auto_detect_on_import: bool = False  # CSV取り込み時に自動検出
```

### 10.12 初期化・マイグレーション

```python
# src/household_mcp/database/db_manager.py

class DatabaseManager:
    """データベース初期化とマイグレーション"""

    def __init__(self, db_path: str = "data/household.db"):
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}")

    def init_db(self):
        """データベースとテーブルの初期化"""
        Base.metadata.create_all(self.engine)
        print(f"Database initialized: {self.db_path}")

    def get_session(self):
        """セッション取得"""
        Session = sessionmaker(bind=self.engine)
        return Session()

    def check_db_exists(self) -> bool:
        """データベースファイルの存在確認"""
        return os.path.exists(self.db_path)
```

---

## 11. Webアプリケーション設計（FR-018対応）

### 11.1 アーキテクチャ概要

```text
┌─────────────────┐    HTTP (REST API)    ┌──────────────────────┐
│  Webブラウザ    │ ◄─────────────────► │ FastAPI HTTPサーバー │
│  (frontend/)    │   (localhost:8000)    │ (http_server.py)     │
└─────────────────┘                       └──────────┬───────────┘
                                                      │
                                                      │ データ取得
                                                      ▼
                                            ┌──────────────────┐
                                            │ HouseholdDataLoader│
                                            │ (dataloader.py)    │
                                            └──────────┬─────────┘
                                                      │
                                                      ▼
                                            ┌──────────────────┐
                                            │  CSV Files       │
                                            │  (data/*.csv)    │
                                            └──────────────────┘
```

### 11.2 ディレクトリ構造

```text
frontend/
├── index.html              # メインHTML（SPA風UI）
├── css/
│   └── style.css          # レスポンシブCSSスタイル
├── js/
│   ├── api.js             # API通信クライアント
│   ├── chart.js           # Chart.js統合・グラフ管理
│   └── main.js            # アプリケーションロジック
└── README.md              # Webアプリのドキュメント
```

### 11.3 REST APIエンドポイント設計

#### 新規追加エンドポイント（http_server.py）

| エンドポイント            | メソッド | 説明                   | レスポンス形式     |
| ------------------------- | -------- | ---------------------- | ------------------ |
| `/api/monthly`            | GET      | 月次データ取得         | JSON（取引リスト） |
| `/api/available-months`   | GET      | 利用可能な年月一覧     | JSON（年月リスト） |
| `/api/category-hierarchy` | GET      | カテゴリ階層情報       | JSON（階層構造）   |
| `/api/charts/{chart_id}`  | GET      | チャート画像（既存）   | PNG画像ストリーム  |
| `/api/cache/stats`        | GET      | キャッシュ統計（既存） | JSON               |
| `/health`                 | GET      | ヘルスチェック（既存） | JSON               |

#### `/api/monthly` 詳細

**パラメータ:**

- `year` (int, required): 年
- `month` (int, required): 月（1-12）
- `output_format` (str, optional): 出力形式（"json" または "image"）
- `graph_type` (str, optional): グラフタイプ（"pie", "bar", "line", "area"）
- `image_size` (str, optional): 画像サイズ（例: "800x600"）

**レスポンス例（JSON形式）:**

```json
{
  "success": true,
  "year": 2025,
  "month": 1,
  "data": [
    {
      "日付": "2025-01-01T00:00:00",
      "内容": "食材購入",
      "大項目": "食費",
      "金額（円）": -3500
    }
  ],
  "count": 243
}
```

#### `/api/available-months` 詳細

**レスポンス例:**

```json
{
  "success": true,
  "months": [
    {"year": 2022, "month": 1},
    {"year": 2022, "month": 2},
    {"year": 2025, "month": 6}
  ]
}
```

### 11.4 フロントエンド設計

#### 技術スタック

- **言語**: JavaScript ES6+（Vanilla JS）
- **チャートライブラリ**: Chart.js 4.4.0（CDN経由）
- **スタイリング**: カスタムCSS（CSS Variables + Flexbox/Grid）
- **通信**: Fetch API（非同期）

#### コンポーネント設計

##### APIClient (api.js)

```javascript
class APIClient {
  - baseUrl: string
  + get(endpoint, params): Promise<Object>
  + getAvailableMonths(): Promise<Array>
  + getMonthlyData(year, month, ...): Promise<Object>
  + getCategoryHierarchy(year, month): Promise<Object>
  + getChartImageUrl(chartId): string
  + healthCheck(): Promise<Object>
}
```

##### ChartManager (chart.js)

```javascript
class ChartManager {
  - canvas: HTMLCanvasElement
  - chart: Chart
  + createPieChart(data): void
  + createBarChart(data): void
  + createLineChart(data): void
  + destroy(): void
  + aggregateByCategory(data): Object
  + aggregateByDate(data): Object
  + generateColors(count): Array<string>
}
```

##### Application (main.js)

```javascript
// グローバル状態管理
- apiClient: APIClient
- chartManager: ChartManager
- currentData: Array
- availableMonths: Array

// 主要機能
+ loadAvailableMonths(): Promise<void>
+ loadMonthlyData(year, month): Promise<void>
+ updateSummaryStats(data): void
+ updateChart(data): void
+ updateTable(data): void
+ filterTable(): void
+ showLoading(show): void
+ showError(message): void
```

#### レスポンシブデザイン

- **PC**: 3カラムレイアウト、グラフ横並び
- **タブレット**: 2カラム、統計カード2x2配置
- **モバイル**: 1カラム、縦積み、タッチ最適化

#### カラースキーム（CSS Variables）

```css
--primary-color: #3b82f6
--secondary-color: #10b981
--danger-color: #ef4444
--bg-color: #f8fafc
--card-bg: #ffffff
```

### 11.6 データフロー

```text
1. ページ読み込み
   → loadAvailableMonths() → GET /api/available-months
   → 年月セレクトボックス生成

2. データ読み込みボタンクリック
   → loadMonthlyData(year, month) → GET /api/monthly
   → updateSummaryStats() → 統計カード更新
   → updateChart() → Chart.js描画
   → updateTable() → テーブルHTML生成
   → updateCategoryFilter() → フィルタ選択肢更新

3. 検索・フィルタ入力
   → filterTable() → DOM操作でtr表示/非表示

4. グラフタイプ変更
   → updateChart() → Chart.js再描画
```

### 11.7 エラーハンドリング

- **ネットワークエラー**: エラーメッセージ表示 + リトライ提案
- **APIエラー（4xx/5xx）**: HTTPステータスとエラー詳細を表示
- **データ未取得**: 空状態のUIを表示
- **CORS問題**: サーバー側でCORS設定が必要（http_server.pyで対応済み）

### 11.8 セキュリティ考慮事項

- **XSS対策**: `escapeHtml()`関数でユーザー入力をエスケープ
- **CORS設定**: FastAPIで`allow_origins=["*"]`（開発用、本番では制限推奨）
- **CSP**: 将来的にContent-Security-Policyヘッダー追加を検討
- **入力検証**: APIリクエストパラメータのバリデーション

### 11.9 パフォーマンス最適化

- **キャッシング**: ブラウザキャッシュ（静的ファイル）
- **遅延読み込み**: Chart.js CDN、画像の遅延読み込み
- **DOM操作最適化**: 一括innerHTML更新、documentFragmentの活用
- **デバウンス**: 検索入力にデバウンス適用（将来拡張）

### 11.10 テスト方針

- **手動テスト**: 各ブラウザ（Chrome, Firefox, Safari, Edge）で動作確認
- **レスポンシブテスト**: デベロッパーツールでモバイル/タブレット表示確認
- **API統合テスト**: curlでエンドポイント動作確認
- **E2Eテスト**: 将来的にPlaywright/Puppeteerを検討

---

## 12. MCP ツール実行フロントエンド設計（FR-021対応）

### 12.1 概要

FR-021では、フロントエンドから利用可能なMCPツールを手動で実行できるUIを提供します。ユーザーが各ツールをカード形式のギャラリーから選択し、パラメータを入力して実行結果を確認できる仕組みです。

### 12.2 ページ構成

#### 12.2.1 トップページ修正（index.html）

現在の `index.html` ナビゲーションに分岐リンクを追加：

```html
<nav class="main-nav">
    <a href="index.html" class="active">メイン画面</a>
    <a href="mcp-tools.html">🔧 MCPツール実行</a>
    <a href="duplicates.html">重複検出</a>
</nav>
```

#### 12.2.2 新ページ `mcp-tools.html`

- 標準的なHTMLテンプレート、Chart.js CDN、スタイルシート参照
- `<div id="tools-gallery">` にカード群を動的挿入
- モーダルダイアログ用の `<div id="execute-modal">` を定義
- `<script src="js/mcp-tools.js"></script>` で機能実装

### 12.3 API設計

#### 12.3.1 ツール一覧取得

```http
GET /api/tools
```

Response: `{ success: true, tools: [ { name, display_name, description, category, parameters } ] }`

#### 12.3.2 ツール詳細取得

```http
GET /api/tools/{tool_name}
```

Response: `{ success: true, tool: { ... } }`

#### 12.3.3 ツール実行

```http
POST /api/tools/{tool_name}/execute
```

Body: `{ year, month, ... }`

Response: `{ success: true, tool_name, execution_time_ms, result }`

### 12.4 フロントエンド実装

**ファイル構成**:

- `frontend/mcp-tools.html` - メインページ
- `frontend/css/mcp-tools.css` - ギャラリー・モーダルスタイル
- `frontend/js/mcp-tools.js` - ツール管理・実行ロジック

**主な機能**:

- API からツール定義取得 → カードレイアウト生成
- 「実行」ボタン → パラメータ入力モーダル表示
- パラメータ型に応じた入力フィールド生成（文字列、数値、日付、選択肢）
- ツール実行 → 結果表示（テキスト/テーブル/グラフ）

### 12.5 バックエンド API実装

**HTTPサーバー（http_server.py）に追加**:

- `GET /api/tools` - ツール一覧定義を返す
- `GET /api/tools/{tool_name}` - 指定ツール詳細を返す  
- `POST /api/tools/{tool_name}/execute` - ツール実行（MCP ツール関数を呼び出し）

---

## 13. 資産推移分析機能設計（FR-022対応）

### 13.1 概要

FR-022では、複数の資産クラス（現金、株、投資信託、不動産、年金）の時系列データを手動登録・管理し、資産推移を可視化・分析する機能を実装します。資産データは独立したテーブルで管理され、将来の家計簿連携に備えた設計となっています。

#### 主要機能

1. **資産クラス管理**（追加・編集・削除）
2. **資産レコード管理**（CRUD 操作）
3. **資産推移グラフ**（Chart.js による可視化）
4. **月次レポート**（CSV エクスポート）
5. **ダッシュボード統合**（進捗状況の一元管理）

---

### 13.2 データベース設計

#### 13.2.1 資産クラステーブル（assets_classes）

```sql
CREATE TABLE IF NOT EXISTS assets_classes (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    description TEXT,
    icon TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

初期データ（5つの資産クラス）:

| id  | name       | display_name | description    | icon |
| --- | ---------- | ------------ | -------------- | ---- |
| 1   | cash       | 現金         | 現金・預金     | 💰    |
| 2   | stocks     | 株           | 国内株・外国株 | 📈    |
| 3   | funds      | 投資信託     | 投資信託全般   | 📊    |
| 4   | realestate | 不動産       | 土地・建物等   | 🏠    |
| 5   | pension    | 年金         | 確定拠出年金等 | 🎯    |

#### 13.2.2 資産レコードテーブル（asset_records）

```sql
CREATE TABLE IF NOT EXISTS asset_records (
    id INTEGER PRIMARY KEY,
    record_date DATE NOT NULL,
    asset_class_id INTEGER NOT NULL REFERENCES assets_classes(id),
    sub_asset_name TEXT NOT NULL,
    amount INTEGER NOT NULL,  -- JPY, 単位: 円
    memo TEXT,
    is_deleted BOOLEAN DEFAULT FALSE,
    is_manual BOOLEAN DEFAULT TRUE,
    source_type TEXT DEFAULT 'manual',  -- 'manual', 'linked', 'calculated'
    linked_transaction_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE,
    created_by TEXT DEFAULT 'user'
);

CREATE INDEX IF NOT EXISTS idx_asset_records_date ON asset_records(record_date);
CREATE INDEX IF NOT EXISTS idx_asset_records_class ON asset_records(asset_class_id);
CREATE INDEX IF NOT EXISTS idx_asset_records_is_deleted ON asset_records(is_deleted);
```

### 13.3 API エンドポイント設計

### 13.4 FR-037 非同期画像ストリーミング安定化 設計

#### 現状分析

- `ImageStreamer` は単純な `async for` + `await asyncio.sleep()` によりチャンク配信。
- イベントループ競合エラー（"Runner is closed" / "Cannot run the event loop while another loop is running"）が pytest(anyio) 実行時に断続的に発生。
- 同期フォールバック `stream_bytes_sync` はテストで利用されるが、要件上必須ではない。

#### 問題要因仮説

1. anyio マーカーがモジュール全体に付与され同期テストもイベントループ管理対象になっている。
2. 他テストまたはフィクスチャで FastAPI/Uvicorn のイベントループ終了後に `ImageStreamer` が再利用される。
3. グローバルキャッシュモジュール import 時の副作用でループ参照状態が不整合。

#### 設計方針

- ループ検出: `asyncio.get_running_loop()` で単一判定、成功時は async generator、失敗時は同期フォールバック（削除選択時は単純に bytes 分割関数）へ。
- 同期フォールバックの扱い: オプション機能化。削除する場合は互換 API を維持（クラス属性/メソッド署名変化なし）。
- テスト分離: `tests/unit/streaming/test_image_streamer_async.py` と `tests/unit/streaming/test_image_streamer_sync.py` に分離。anyio マーカーは async 側のみ。
- 並行テスト: `tests/integration/test_streaming_concurrency.py` で 5 並行要求（`asyncio.gather`）し全チャンク到達と 0.5s 以内応答確認。
- カバレッジ目標: `image_streamer.py` 分岐/行 90% 以上（TS-053）。
- FastAPI 統合: `create_response` の body に async generator を渡し、同期フォールバック利用時も StreamingResponse が正常動作することを検証。
- ロギング: ループモード選択時に DEBUG ログ（"ImageStreamer mode=async" / "mode=sync"）。

#### 影響範囲と非互換リスク

- sync メソッド削除時: 既存の直接呼び出しテストが失敗 → 残すかラッパーで非推奨化。
- 非同期のみへ統一: 単純化による保守性向上。高負荷時の CPU sleep を `await asyncio.sleep(delay)` に一本化。

#### API/インターフェース変更（案）

```python
class ImageStreamer:
    def __init__(self, chunk_size: int = 8192, enable_sync_fallback: bool = False):
        self.chunk_size = chunk_size
        self.enable_sync_fallback = enable_sync_fallback

    async def stream_bytes(self, image_data: bytes, delay_ms: float = 0.01):
        for i in range(0, len(image_data), self.chunk_size):
            yield image_data[i:i+self.chunk_size]
            if delay_ms > 0:
                await asyncio.sleep(delay_ms)

    def _stream_bytes_sync(self, image_data: bytes, delay_ms: float = 0.01):  # 非公開化
        import time
        for i in range(0, len(image_data), self.chunk_size):
            yield image_data[i:i+self.chunk_size]
            if delay_ms > 0:
                time.sleep(delay_ms)

    def create_response(...):
        try:
            asyncio.get_running_loop()
            body = self.stream_bytes(image_data)
        except RuntimeError:
            if self.enable_sync_fallback:
                body = self._stream_bytes_sync(image_data)
            else:
                # ループなし環境では簡易 async ランナーで包む（低頻度利用）
                async def _one_shot():
                    async for c in self.stream_bytes(image_data):
                        yield c
                body = _one_shot()
        return StreamingResponse(body, media_type=media_type)
```

#### テスト計画

| テストID | 目的                    | ファイル                        | 検証内容                       |
| -------- | ----------------------- | ------------------------------- | ------------------------------ |
| TS-050   | 非同期チャンク正常      | `test_image_streamer_async.py`  | 全チャンク・順序・サイズ       |
| TS-051   | 5並行ストリーム         | `test_streaming_concurrency.py` | gather後例外なし & 時間制約    |
| TS-052   | syncフォールバック選択  | `test_image_streamer_sync.py`   | enable_sync_fallback=True 動作 |
| TS-053   | カバレッジ ≥90%         | coverage レポート               | 分岐/行達成                    |
| TS-054   | StreamingResponseヘッダ | concurrency テスト内            | Content-Type/Disposition       |

#### 成功指標

- 例外再発率 0%（対象エラー）
- レスポンスタイム（5並行、<0.5s）
- カバレッジ目標達成

#### ロールバック戦略

- 新クラス初期化フラグ `enable_sync_fallback` を残すことで、非同期統一で問題があれば sync 経由へ即切り替え可能。
- 旧テスト保持期間（暫定）: 1 フェーズ（次マイナーバージョン）

#### 13.3.1 資産クラス取得

```http
GET /api/assets/classes
```

Response:

```json
{
  "success": true,
  "classes": [
    {
      "id": 1,
      "name": "cash",
      "display_name": "現金",
      "description": "現金・預金",
      "icon": "💰"
    },
    ...
  ]
}
```

#### 13.3.2 資産レコード一覧取得

```http
GET /api/assets/records
Query Parameters:
  - asset_class_id: INTEGER (optional)
  - start_date: DATE (optional, YYYY-MM-DD)
  - end_date: DATE (optional, YYYY-MM-DD)
  - include_deleted: BOOLEAN (default: false)
```

Response:

```json
{
  "success": true,
  "records": [
    {
      "id": 1,
      "record_date": "2025-01-31",
      "asset_class_id": 1,
      "asset_class_name": "現金",
      "sub_asset_name": "普通預金",
      "amount": 1000000,
      "memo": "給与振込",
      "created_at": "2025-01-31T00:00:00Z",
      "updated_at": "2025-01-31T00:00:00Z"
    },
    ...
  ],
  "total_count": 100
}
```

#### 13.3.3 資産レコード登録

```http
POST /api/assets/records
```

Request:

```json
{
  "record_date": "2025-02-28",
  "asset_class_id": 1,
  "sub_asset_name": "普通預金",
  "amount": 1050000,
  "memo": "給与振込"
}
```

Response:

```json
{
  "success": true,
  "record": {
    "id": 2,
    "record_date": "2025-02-28",
    "asset_class_id": 1,
    "asset_class_name": "現金",
    "sub_asset_name": "普通預金",
    "amount": 1050000,
    "memo": "給与振込",
    "created_at": "2025-02-28T00:00:00Z"
  }
}
```

#### 13.3.4 資産レコード編集

```http
PUT /api/assets/records/{record_id}
```

Request: 上記 POST と同様（更新するフィールドのみ指定可）

Response: 更新後のレコード

#### 13.3.5 資産レコード削除

```http
DELETE /api/assets/records/{record_id}
```

Response:

```json
{
  "success": true,
  "message": "レコードを削除しました"
}
```

#### 13.3.6 資産集計（月末時点）

```http
GET /api/assets/summary
Query Parameters:
  - start_year: INTEGER
  - start_month: INTEGER
  - end_year: INTEGER
  - end_month: INTEGER
  - fill_method: 'forward_fill' | 'zero' (default: 'forward_fill')
```

Response:

```json
{
  "success": true,
  "summary": {
    "2025-01": {
      "1": 1000000,      // 資産クラスID 1 (現金): 1,000,000 円
      "2": 500000,       // 資産クラスID 2 (株): 500,000 円
      ...
      "total": 2500000
    },
    "2025-02": {
      ...
    }
  },
  "classes": {
    "1": "現金",
    "2": "株",
    ...
  }
}
```

#### 13.3.7 資産配分（月末時点）

```http
GET /api/assets/allocation
Query Parameters:
  - year: INTEGER
  - month: INTEGER
```

Response:

```json
{
  "success": true,
  "allocation": [
    {
      "asset_class_id": 1,
      "asset_class_name": "現金",
      "amount": 1000000,
      "percentage": 40.0
    },
    {
      "asset_class_id": 2,
      "asset_class_name": "株",
      "amount": 800000,
      "percentage": 32.0
    },
    ...
  ],
  "total_assets": 2500000
}
```

#### 13.3.8 資産エクスポート（CSV）

```http
GET /api/assets/export
Query Parameters:
  - format: 'csv' (required)
  - start_date: DATE (optional)
  - end_date: DATE (optional)
  - asset_class_id: INTEGER (optional)
```

Response: CSV ファイル（`Content-Disposition: attachment` で返却）

### 13.4 バックエンド実装構成

新規モジュール追加:

```text
backend/src/household_mcp/
├── assets/
│   ├── __init__.py
│   ├── models.py              # SQLAlchemy/Pydantic モデル
│   ├── manager.py             # 資産データ操作（CRUD）
│   ├── analyzer.py            # 集計・分析ロジック
│   └── exporter.py            # CSV エクスポート処理
└── web/
    └── routes/
        └── assets_routes.py    # FastAPI ルートハンドラ
```

#### 13.4.1 models.py

```python
from pydantic import BaseModel
from typing import Optional
from datetime import date

class AssetClassModel(BaseModel):
    id: int
    name: str
    display_name: str
    description: Optional[str] = None
    icon: Optional[str] = None

class AssetRecordModel(BaseModel):
    id: Optional[int] = None
    record_date: date
    asset_class_id: int
    sub_asset_name: str
    amount: int  # JPY
    memo: Optional[str] = None
    is_manual: bool = True
    source_type: str = 'manual'

class AssetSummaryModel(BaseModel):
    year: int
    month: int
    summary: dict  # { class_id: amount, ... }
    total: int
```

#### 13.4.2 manager.py

主要メソッド:

```python
class AssetManager:
    def __init__(self, db_path: str):
        self.db = DatabaseManager(db_path)

    def create_record(self, record: AssetRecordModel) -> AssetRecordModel: ...
    def get_records(self, filters: dict) -> List[AssetRecordModel]: ...
    def update_record(self, record_id: int, data: dict) -> AssetRecordModel: ...
    def delete_record(self, record_id: int) -> bool: ...
    def get_classes(self) -> List[AssetClassModel]: ...
```

#### 13.4.3 analyzer.py

```python
class AssetAnalyzer:
    def get_summary(self, start_year: int, start_month: int,
                    end_year: int, end_month: int,
                    fill_method: str = 'forward_fill') -> dict: ...

    def get_allocation(self, year: int, month: int) -> List[dict]: ...

    def get_monthly_snapshot(self, year: int, month: int) -> dict: ...
```

### 13.5 フロントエンド実装

#### 13.5.1 ページ構成

新ページ `assets.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <title>資産管理 | 家計簿分析</title>
    <link rel="stylesheet" href="css/style.css">
    <link rel="stylesheet" href="css/assets.css">
</head>
<body>
    <nav class="main-nav">
        <a href="index.html">📊 月次分析</a>
        <a href="assets.html" class="active">💰 資産管理</a>
        <a href="financial-independence.html">🎯 経済的自由</a>
        <a href="mcp-tools.html">🔧 MCPツール</a>
    </nav>

    <div class="container">
        <h1>資産管理</h1>

        <!-- 資産登録フォーム -->
        <section id="asset-form-section">
            <h2>資産登録</h2>
            <form id="asset-form">
                <input type="date" id="record-date" required>
                <select id="asset-class" required>
                    <!-- 動的挿入 -->
                </select>
                <input type="text" id="sub-asset-name" placeholder="サブ資産名" required>
                <input type="number" id="amount" placeholder="金額（円）" required>
                <textarea id="memo" placeholder="メモ（オプション）"></textarea>
                <button type="submit">登録</button>
            </form>
        </section>

        <!-- 資産一覧テーブル -->
        <section id="asset-list-section">
            <h2>資産一覧</h2>
            <table id="asset-table">
                <thead>
                    <tr>
                        <th>登録日</th>
                        <th>資産クラス</th>
                        <th>サブ資産名</th>
                        <th>金額</th>
                        <th>アクション</th>
                    </tr>
                </thead>
                <tbody id="asset-tbody">
                </tbody>
            </table>
        </section>

        <!-- 期間選択 -->
        <section id="period-selection">
            <h2>期間選択</h2>
            <div class="period-controls">
                <button class="preset-btn" data-preset="3m">直近3ヶ月</button>
                <button class="preset-btn" data-preset="6m">直近6ヶ月</button>
                <button class="preset-btn" data-preset="12m">直近12ヶ月</button>
                <button class="preset-btn" data-preset="all">全期間</button>
                <input type="date" id="custom-start">
                <input type="date" id="custom-end">
                <button id="apply-custom-period">適用</button>
            </div>
        </section>

        <!-- グラフタブ -->
        <section id="chart-section">
            <div class="chart-tabs">
                <button class="chart-tab-btn active" data-tab="trend">推移グラフ</button>
                <button class="chart-tab-btn" data-tab="allocation">配分（月末時点）</button>
            </div>

            <div id="trend-tab" class="chart-tab-content active">
                <canvas id="trend-chart"></canvas>
            </div>

            <div id="allocation-tab" class="chart-tab-content">
                <canvas id="allocation-chart"></canvas>
            </div>
        </section>

        <!-- 統計サマリー -->
        <section id="summary-section">
            <h2>統計サマリー</h2>
            <div class="summary-grid">
                <div class="summary-card">
                    <div class="label">合計資産額</div>
                    <div class="value" id="total-assets">-</div>
                </div>
                <div class="summary-card">
                    <div class="label">前月比</div>
                    <div class="value" id="month-on-month">-</div>
                </div>
                <div class="summary-card">
                    <div class="label">最大資産額</div>
                    <div class="value" id="max-assets">-</div>
                </div>
            </div>
        </section>
    </div>

    <!-- 編集モーダル -->
    <div id="edit-modal" class="modal">
        <div class="modal-content">
            <h3>資産情報編集</h3>
            <form id="edit-form">
                <!-- 登録フォームと同じフィールド -->
                <button type="submit">更新</button>
                <button type="button" id="close-modal">キャンセル</button>
            </form>
        </div>
    </div>

    <script src="js/assets.js"></script>
</body>
</html>
```

#### 13.5.2 スタイル（css/assets.css）

- フォーム、テーブル、グラフ、カードレイアウト
- レスポンシブデザイン（モバイル・タブレット・PC対応）
- 資産クラスアイコンの表示

#### 13.5.3 JavaScript（js/assets.js）

主要機能:

```javascript
class AssetManager {
    constructor() {
        this.apiBase = '/api/assets';
        this.init();
    }

    async init() {
        await this.loadClasses();
        await this.loadRecords();
        this.setupEventListeners();
    }

    async loadClasses() { ... }
    async loadRecords(filters = {}) { ... }
    async createRecord(data) { ... }
    async updateRecord(id, data) { ... }
    async deleteRecord(id) { ... }
    async loadSummary(startYear, startMonth, endYear, endMonth) { ... }
    async loadAllocation(year, month) { ... }

    renderRecordsTable(records) { ... }
    renderTrendChart(summaryData) { ... }
    renderAllocationChart(allocationData) { ... }
    setupEventListeners() { ... }
}

const manager = new AssetManager();
```

### 13.6 統合ポイント

#### 13.6.1 トップページナビゲーション修正

`frontend/index.html` のナビゲーションに「資産管理」リンクを追加:

```html
<nav class="main-nav">
    <a href="index.html">📊 月次分析</a>
    <a href="assets.html">💰 資産管理</a>
    <a href="financial-independence.html">🎯 経済的自由</a>
    <a href="mcp-tools.html">🔧 MCPツール</a>
</nav>
```

#### 13.6.2 HTTPサーバーに新ルート追加

`backend/src/household_mcp/web/http_server.py` に以下を追加:

```python
from household_mcp.web.routes import assets_routes

app.include_router(assets_routes.router, prefix="/api")
```

#### 13.6.3 データベース初期化

`backend/src/household_mcp/database/manager.py` に `initialize_assets_tables()` メソッドを追加

### 13.7 テスト戦略

#### 13.7.1 ユニットテスト

```python
# tests/test_financial_independence_analyzer.py
def test_calculate_fire_target():
    expenses = pd.Series([200000] * 12)
    target = calculate_fire_target(expenses)
    assert target == 200000 * 12 * 25  # 60,000,000

def test_classify_expenses():
    # 定常：毎月50,000円
    # 臨時：3ヶ月だけ100,000円
    df = create_test_expense_data()
    classifications = classify_expenses(df)
    assert classifications['食費'] == 'regular'
    assert classifications['旅行費'] == 'irregular'

def test_calculate_months_to_fi():
    months = calculate_months_to_fi(
        current_assets=5000000,
        target_assets=7500000,
        monthly_rate=0.02
    )
    assert 20 <= months <= 30  # おおよそ25ヶ月
```

#### 13.7.2 統合テスト

```python
# tests/test_fi_api.py
async def test_get_status_endpoint(client):
    response = await client.get("/api/financial-independence/status")
    assert response.status_code == 200
    data = response.json()
    assert 'current_assets' in data
    assert 'target_assets' in data
    assert 'progress_rate' in data
```

#### 13.7.3 手動テスト

- 資産登録・編集・削除
- グラフ表示と期間指定
- CSV エクスポート

---

## 14. 家計改善機能強化設計（FR-021〜FR-024対応）

### 14.1 概要

本セクションでは、これまでダミーデータで動作していた分析・改善提案ツールを実データ連携させ、実用的な家計改善支援機能へと昇華させるための設計を定義する。

### 14.2 ツール実装設計

#### 14.2.1 支出パターン分析 (`analyze_expense_patterns`)

- **データソース**: `HouseholdDataLoader` を使用して直近12ヶ月（パラメータ指定可）のCSVデータをロード。
- **処理**: `ExpensePatternAnalyzer` を使用して、カテゴリごとの定期/変動/異常判定を行う。
- **出力**: 定期支出と変動支出の比率、各カテゴリの分類結果を返す。

#### 14.2.2 家計改善提案 (`suggest_improvement_actions`)

- **データソース**: 直近12ヶ月の実支出データ。
- **ロジック**:
  1. **変動費の削減**: 変動費と判定されたカテゴリのうち、増加トレンドにあるもの、または平均より高い月があるものを特定。
  2. **固定費の見直し**: 定期支出と判定されたカテゴリのうち、金額が大きいもの（住居費、保険など）に対して一般的な見直し提案を行う。
- **出力**: 優先度付きのアクションリスト。

#### 14.2.3 支出異常検知 (`detect_spending_anomalies`)

- **データソース**: 直近6〜12ヶ月の実支出データ。
- **ロジック**:
  - 各カテゴリの過去平均($\mu$)と標準偏差($\sigma$)を計算。
  - 当月の支出($x$)が $x > \mu + 2\sigma$ (閾値は調整可) となるカテゴリを検出。
- **出力**: 異常検知されたカテゴリ、金額、乖離度（何シグマか）。

#### 14.2.4 FIREシミュレーション (`project_financial_independence_date`)

- **データソース**:
  - **現在資産**: `FireSnapshotService` から最新のスナップショットを取得。データがない場合は0またはユーザー入力を要求。
  - **年間支出**: 直近12ヶ月の実支出合計を使用。
- **処理**: `FinancialIndependenceAnalyzer` を使用して、現状のペースでのFIRE達成時期を計算。追加貯蓄額による短縮効果もシミュレーションする。

### 14.3 クラス設計

#### 14.3.1 `ExpensePatternAnalyzer` (既存拡張)

既存の `backend/src/household_mcp/analysis/expense_pattern_analyzer.py` を活用する。
データロード部分は `HouseholdDataLoader` に委譲し、Analyzerは純粋な数値分析に集中させる。

#### 14.3.2 `AnomalyDetector` (新規/既存活用)

`ExpensePatternAnalyzer` 内に異常検知ロジックが含まれているため、これを活用するラッパー関数またはクラスを `financial_independence_tools.py` 内に実装する。
