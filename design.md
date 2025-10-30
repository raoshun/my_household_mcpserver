# 家計簿分析 MCP サーバー設計書

- **バージョン**: 0.5.0
- **更新日**: 2025-10-30
- **作成者**: GitHub Copilot (AI assistant)
- **対象要件**: [requirements.md](./requirements.md) に記載の FR-001〜FR-017、NFR-001〜NFR-013

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
- データソースは `data/` 配下の家計簿 CSV ファイルとSQLiteデータベース（全てローカル）。外部ネットワーク通信は行わない。
- SQLiteは重複検出結果の永続化に使用（data/household.db）。
- 解析ロジックは pandas/numpy によるインメモリ処理で完結する。

### 1.2 コンポーネント構成

| コンポーネント    | 主な責務                            | 主な実装                                           | 対応要件        |
| ----------------- | ----------------------------------- | -------------------------------------------------- | --------------- |
| MCP Server        | リソース/ツール定義とリクエスト分岐 | `src/server.py`                                    | 全要件          |
| Data Loader       | CSV ファイルの読み込みと前処理      | `src/household_mcp/dataloader.py`                  | FR-001〜FR-003  |
| Trend Analyzer    | 月次指標計算モジュール              | `src/household_mcp/analysis/trends.py`             | FR-001, FR-005  |
| Query Resolver    | 質問パラメータ解釈ユーティリティ    | `src/household_mcp/utils/query_parser.py`          | FR-002, FR-003  |
| Formatter         | 数値書式・テキスト生成              | `src/household_mcp/utils/formatters.py`            | NFR-008         |
| DatabaseManager   | SQLiteセッション管理と初期化        | `src/household_mcp/database/manager.py`            | FR-009, NFR-013 |
| CSVImporter       | CSV→DBインポート処理                | `src/household_mcp/database/csv_importer.py`       | FR-009-3        |
| DuplicateDetector | 重複検出アルゴリズム                | `src/household_mcp/duplicate/detector.py`          | FR-009-1        |
| ChartGenerator    | グラフ画像生成（matplotlib使用）    | `src/household_mcp/visualization/chart_generator.py` | FR-015          |
| ImageStreamer     | 画像ストリーミング配信              | `src/household_mcp/streaming/image_streamer.py`    | FR-016          |
| HTTPServer        | FastAPI HTTPエンドポイント          | `src/household_mcp/http_server.py`                 | FR-016          |
| ChartCache        | 画像キャッシング管理                | `src/household_mcp/streaming/chart_cache.py`       | FR-016, NFR-005 |
| EnhancedTools     | MCPツールの画像生成拡張             | `src/household_mcp/tools/enhanced_tools.py`        | FR-017          |

### 1.3 技術スタック

| 区分         | 採用技術                             | 備考                  |
| ------------ | ------------------------------------ | --------------------- |
| 言語         | Python 3.12 (uv 管理)                | `pyproject.toml` 参照 |
| MCP 実装     | `fastmcp`                            | 既存コードで使用      |
| データ処理   | pandas, numpy                        | CSV の集計と指標算出  |
| データベース | SQLite (better-sqlite3)              | 重複判定結果の永続化  |
| 可視化       | matplotlib>=3.8.0, plotly>=5.17.0    | グラフ画像生成        |
| 画像処理     | pillow>=10.0.0                       | 画像フォーマット変換  |
| HTTP         | FastAPI>=0.100.0, uvicorn>=0.23.0    | 画像配信エンドポイント |
| キャッシング | cachetools>=5.3.0                    | 画像キャッシュ管理    |
| フォーマット | Python 標準 `locale`, `decimal` など | 数値の桁区切り、丸め  |
| テスト       | pytest, pytest-asyncio               | 単体・統合テスト      |

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

| 要件                     | 設計対応                                                                                         |
| ------------------------ | ------------------------------------------------------------------------------------------------ |
| NFR-001 (応答表現)       | `format_currency` と `format_percentage` で桁区切り・丸めを統一する。                            |
| NFR-002 (パフォーマンス) | pandas 処理は 12 か月分の明細（数千行想定）を 1 秒以内で完了し、結果を簡易キャッシュに保持する。 |
| NFR-003 (信頼性)         | 例外クラスを通じて原因別メッセージを返却し、CSV 読み込み時には対象ファイル名をログに記録。       |
| NFR-004 (セキュリティ)   | 全処理をローカル内で完結させ、ログにも個人情報を残さない。外部通信は行わない。                   |

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
    """CSV → DB インポーター"""

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
│   │   └── tools/
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

## 11. 変更履歴

| 日付       | バージョン | 概要                                                 |
| ---------- | ---------- | ---------------------------------------------------- |
| 2025-07-29 | 1.0        | 旧バージョン（DB 前提の構成）                        |
| 2025-10-03 | 0.2.0      | CSV 前提アーキテクチャに刷新、トレンド分析設計を追加 |
| 2025-10-04 | 0.3.0      | 画像生成・HTTPストリーミング機能設計を追加           |
| 2025-10-30 | 0.4.0      | 重複検出・解決機能設計を追加（FR-009対応）           |

---

以上。
