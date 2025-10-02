# 家計簿分析 MCP サーバー設計書

- **バージョン**: 0.2.0
- **更新日**: 2025-10-03
- **作成者**: GitHub Copilot (AI assistant)
- **対象要件**: [requirements.md](./requirements.md) に記載の FR-001〜FR-003、NFR-001〜NFR-004

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

- サーバーは `fastmcp.FastMCP` を利用し、LLM クライアントと標準入出力経由で通信する。
- データソースは `data/` 配下の家計簿 CSV ファイル（全てローカル）。外部 DB やネットワーク通信は行わない。
- 解析ロジックは pandas/numpy によるインメモリ処理で完結する。

### 1.2 コンポーネント構成

| コンポーネント | 主な責務 | 主な実装 | 対応要件 |
| --- | --- | --- | --- |
| MCP Server | リソース/ツール定義とリクエスト分岐 | `src/server.py` | 全要件 |
| Data Loader | CSV ファイルの読み込みと前処理 | `src/household_mcp/dataloader.py` | FR-001〜FR-003 |
| Trend Analyzer | 月次指標計算モジュール（今後追加） | `src/household_mcp/analysis/trends.py` *(予定)* | FR-001 |
| Query Resolver | 質問パラメータ解釈ユーティリティ | `src/household_mcp/utils/query_parser.py` *(予定)* | FR-002, FR-003 |
| Formatter | 数値書式・テキスト生成 | `src/household_mcp/utils/formatters.py` *(予定)* | NFR-001 |

### 1.3 技術スタック

| 区分 | 採用技術 | 備考 |
| --- | --- | --- |
| 言語 | Python 3.12 (uv 管理) | `pyproject.toml` 参照 |
| MCP 実装 | `fastmcp` | 既存コードで使用 |
| データ処理 | pandas, numpy | CSV の集計と指標算出 |
| フォーマット | Python 標準 `locale`, `decimal` など | 数値の桁区切り、丸め |
| テスト | pytest | 今後テスト追加予定 |

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

---

## 3. MCP リソース / ツール設計

### 3.1 既存リソース・ツール

| 名称 | 種別 | 概要 | 返却値 |
| --- | --- | --- | --- |
| `data://category_hierarchy` | Resource | 大項目→中項目の階層辞書 | `dict[str, list[str]]` |
| `data://household_categories` | Resource | カテゴリ一覧（`category_hierarchy` と同等） | `dict[str, list[str]]` |
| `data://available_months` | Resource | 利用可能な年月の静的リスト | `list[dict]` |
| `get_monthly_household` | Tool | 指定年月の明細一覧 | `list[dict]` |

### 3.2 追加予定リソース/ツール（トレンド分析）

| 名称 | 種別 | 役割 | 主な入力パラメータ | 対応要件 |
| --- | --- | --- | --- | --- |
| `data://category_trend_summary` | Resource | 直近 12 か月のカテゴリ別指標を返す API | なし（サーバ内部で最新期間を判定） | FR-001 |
| `get_category_trend` | Tool | 質問に応じたカテゴリ/月範囲のトレンド解説を返す | `category`, `start_month`, `end_month`（任意） | FR-002, FR-003 |

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

| ケース | 例外 | メッセージ方針 |
| --- | --- | --- |
| 対象 CSV が見つからない | `FileNotFoundError` → `DataSourceError` | 「データファイルが見つかりません」 |
| 指定カテゴリが存在しない | `ValidationError` | 「該当カテゴリが見つかりません」 |
| データ不足で指標計算不可 | `AnalysisError` | 「対象期間のデータが不足しています」 |

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

| 要件 | 設計対応 |
| --- | --- |
| NFR-001 (応答表現) | `format_currency` と `format_percentage` で桁区切り・丸めを統一する。 |
| NFR-002 (パフォーマンス) | pandas 処理は 12 か月分の明細（数千行想定）を 1 秒以内で完了し、結果を簡易キャッシュに保持する。 |
| NFR-003 (信頼性) | 例外クラスを通じて原因別メッセージを返却し、CSV 読み込み時には対象ファイル名をログに記録。 |
| NFR-004 (セキュリティ) | 全処理をローカル内で完結させ、ログにも個人情報を残さない。外部通信は行わない。 |

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

## 9. 変更履歴

| 日付 | バージョン | 概要 |
| --- | --- | --- |
| 2025-07-29 | 1.0 | 旧バージョン（DB 前提の構成） |
| 2025-10-03 | 0.2.0 | CSV 前提アーキテクチャに刷新、トレンド分析設計を追加 |

---

以上。
