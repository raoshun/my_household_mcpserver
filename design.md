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

## 10. 画像生成・ストリーミング機能設計

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
                                                ▼              └────────────┘
                                      ┌────────────────────────┐
                                      │  CSV データ / ローカルFS │
                                      └────────────────────────┘
```

### 10.2 新規コンポーネント

| コンポーネント | 主な責務 | 実装ファイル | 対応要件 |
| --- | --- | --- | --- |
| Chart Generator | matplotlib/plotlyによるグラフ画像生成 | `src/household_mcp/visualization/chart_generator.py` | FR-004 |
| Image Streamer | HTTPストリーミングによる画像配信 | `src/household_mcp/streaming/image_streamer.py` | FR-005 |
| Tool Extensions | 既存MCPツールの引数拡張とルーティング | `src/household_mcp/tools/enhanced_tools.py` | FR-006 |
| HTTP Server | FastAPI/uvicornによるHTTPエンドポイント | `src/household_mcp/server/http_server.py` | FR-005 |

### 10.3 技術スタック拡張

| 区分 | 追加技術 | 用途 | 備考 |
| --- | --- | --- | --- |
| 画像生成 | matplotlib 3.8+ | グラフ描画ライブラリ | 日本語フォント対応 |
| 画像生成 | pillow 10.0+ | 画像処理・形式変換 | PNG/JPEG出力 |
| HTTP Server | FastAPI 0.100+ | RESTful API・ストリーミング | 非同期処理対応 |
| HTTP Server | uvicorn 0.23+ | ASGI アプリケーションサーバー | 開発・本番両用 |
| 画像フォーマット | io.BytesIO | メモリ内画像データ処理 | Python標準ライブラリ |

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

| グラフタイプ | 適用ツール | データ構造 | 実装方針 |
| --- | --- | --- | --- |
| `pie` | `get_monthly_household` | カテゴリ別支出金額 | matplotlib.pyplot.pie() |
| `bar` | `get_monthly_household` | カテゴリ別支出金額 | matplotlib.pyplot.bar() |
| `line` | `get_category_trend` | 月次推移データ | matplotlib.pyplot.plot() |
| `area` | `get_category_trend` | 月次推移データ | matplotlib.pyplot.fill_between() |

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

| 要件 | 実装方針 |
| --- | --- |
| 画像生成3秒以内 | matplotlib の描画設定最適化、データサイズ制限 |
| メモリ50MB以下 | 生成後の即座開放、BytesIO使用 |
| 転送1MB/秒以上 | 非同期ストリーミング、適切なチャンクサイズ |
| 同時接続5件 | FastAPI の並行処理、コネクションプール |

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

## 11. 変更履歴

| 日付 | バージョン | 概要 |
| --- | --- | --- |
| 2025-07-29 | 1.0 | 旧バージョン（DB 前提の構成） |
| 2025-10-03 | 0.2.0 | CSV 前提アーキテクチャに刷新、トレンド分析設計を追加 |
| 2025-10-04 | 0.3.0 | 画像生成・HTTPストリーミング機能設計を追加 |

---

以上。
