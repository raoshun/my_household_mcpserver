# Household MCP Server

[![CI](https://github.com/raoshun/my_household_mcpserver/actions/workflows/ci.yml/badge.svg)](https://github.com/raoshun/my_household_mcpserver/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/raoshun/my_household_mcpserver/branch/main/graph/badge.svg)](https://codecov.io/gh/raoshun/my_household_mcpserver)
[![Python 3.11-3.14](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

家計簿CSVをインメモリで分析し、AIエージェントとの自然言語会話に必要な情報を提供する MCP（Model Context Protocol）サーバーです。

## 概要

このプロジェクトは、ローカルの家計簿CSV（`data/` 配下）を pandas で分析し、AI エージェントからの自然言語リクエストに応答する MCP サーバーを提供します。ユーザーは複雑なクエリ言語を学ぶことなく、日常会話で家計データの洞察を得ることができます。

### リポジトリ構成（Monorepo）

リポジトリはフロントエンドとバックエンドに分割されています（FR-020）。

- `backend/`: Python 製の MCP/HTTP API サーバー（テストは `backend/tests/`）
- `frontend/`: 静的 Web アプリ（Vanilla JS + Chart.js）。ローカルHTTPサーバで配信。

VS Code のタスク（.vscode/tasks.json）がモノレポ構成に対応しています。

- バックエンドの開発: 「Install Dependencies」「Run Tests」「Start HTTP API Server」
- 追加依存の導入: 「Install Web/Streaming Extras」（FastAPI/uvicorn/SQLAlchemyなど）
- フロントエンドの起動: 「Start Frontend HTTP Server」
- まとめ実行: 「Start Full Stack」（API 8000 + Web 8080）

## 主な機能

- **自然言語インターフェース**: 日本語でカテゴリ別・期間別の支出推移を確認
- **トレンド分析**: 月次集計、前月比・前年同月比・12か月移動平均の計算
- **カテゴリハイライト**: 指定期間で支出が大きいカテゴリを自動抽出
- **MCPツール実行UI**: Web ブラウザから対話的にツール実行、結果表示
- **重複レコード検出**: AIとの会話で重複取引を検出・解消（[詳細](docs/duplicate_detection.md)）
- **ローカル完結設計**: CSV ファイルをローカルで読み込み、外部通信なしで解析

## 要件

- Python 3.12 以上（`uv` を推奨）
- 家計簿 CSV ファイル（`data/収入・支出詳細_YYYY-MM-DD_YYYY-MM-DD.csv` 形式）

## インストール

### 依存最小化ポリシー

本プロジェクトは **依存関係の最小化** を重視しています：

- **コア機能**: 必須依存は4パッケージのみ（pandas, numpy, mcp, fastmcp）
- **オプション機能**: 追加機能はoptional dependenciesとして分離
- **目的**: インストールサイズの削減、依存関係の衝突回避、軽量な実行環境

**設計原則:**

1. MCP サーバーとしての基本機能（CSV読み込み、データ分析、リソース/ツール提供）は最小依存で動作
2. 画像生成、Web API、データベース連携などの拡張機能は必要に応じてインストール
3. 各機能グループは独立しており、必要なものだけを選択可能

### 基本インストール

```bash
# 推奨: uv を用いた基本インストール（MCP サーバーのみ）
uv pip install -e "."

# 代替: pip を使用
pip install -e "."

# 開発環境（テスト・lint含む）
uv pip install -e ".[dev]"
```

### オプション機能の追加

必要な機能に応じて、以下から選択してインストールしてください。

#### 機能別インストールガイド

| 機能                    | オプション      | 用途                                  | 依存パッケージ数 |
| ----------------------- | --------------- | ------------------------------------- | ---------------- |
| **MCP サーバー基本**    | なし            | CSV 読み込み・MCP リソース/ツール提供 | 4 個             |
| **画像生成**            | `visualization` | グラフ・チャート生成（PNG/SVG）       | +3 個            |
| **HTTP ストリーミング** | `streaming`     | FastAPI 経由の画像配信                | +3 個            |
| **Web API**             | `web`           | REST API エンドポイント               | +4 個            |
| **データベース連携**    | `db`            | SQLite/PostgreSQL への永続化          | +2 個            |
| **認証**                | `auth`          | JWT・パスワード認証機能               | +2 個            |
| **非同期 I/O**          | `io`            | aiofiles・httpx 対応                  | +2 個            |
| **構造化ログ**          | `logging`       | structlog による詳細ログ出力          | +1 個            |
| **すべて**              | `full`          | 全機能を有効化                        | +17 個           |

#### インストール例

```bash
# ① 画像生成機能のみ追加（グラフ生成用）
uv pip install -e ".[visualization]"

# ② HTTP ストリーミング対応（FastAPI + uvicorn + キャッシュ）
uv pip install -e ".[streaming]"

# ③ Web API（REST エンドポイント提供）
uv pip install -e ".[web]"

# ④ 複合: 画像生成 + HTTP ストリーミング
uv pip install -e ".[visualization,streaming]"

# ⑤ 開発環境 + 画像生成機能
uv pip install -e ".[dev,visualization]"

# ⑥ 開発環境 + すべての機能（推奨 for development）
uv pip install -e ".[dev,full]"

# ⑦ 本番環境: Web API + ストリーミング + ログ
uv pip install -e ".[web,streaming,logging]"

# ⑧ 完全インストール（すべての機能）
uv pip install -e ".[full]"
```

### 各オプション機能の詳細

#### 🎨 `visualization` - 画像生成機能

支出トレンドをグラフとして PNG/SVG 形式で生成します。

**含まれるパッケージ:**

- `matplotlib >= 3.8.0` - グラフ描画
- `plotly >= 5.17.0` - インタラクティブチャート
- `pillow >= 10.0.0` - 画像処理

**使用例:**

```bash
uv pip install -e ".[visualization]"
python -c "from src.household_mcp.visualization import ChartGenerator; print('OK')"
```

**必要な設定:**

- 日本語フォント配置（`fonts/` ディレクトリに Noto Sans CJK を配置）
- 詳細は下記「日本語フォント設定」を参照

---

#### 🌐 `streaming` - HTTP ストリーミング対応

画像をブラウザから直接配信可能な HTTP サーバー機能を提供します。

**含まれるパッケージ:**

- `fastapi >= 0.100.0` - Web フレームワーク
- `uvicorn[standard] >= 0.23.0` - ASGI サーバー
- `cachetools >= 5.3.0` - キャッシング機構

**使用例:**

```bash
uv pip install -e ".[streaming]"
python -m src.server --transport http --port 8080
```

**依存関係:**

- `visualization` オプションと組み合わせて使用すると、グラフを HTTP 経由で配信可能

---

#### 🔌 `web` - REST API

完全な REST API エンドポイントを公開し、HTTP クライアントからのアクセスを可能にします。

**含まれるパッケージ:**

- `fastapi >= 0.100.0`
- `uvicorn[standard] >= 0.23.0`
- `pydantic >= 2.11, < 3` - リクエスト/レスポンス検証
- `python-multipart >= 0.0.6` - マルチパート形式対応

**使用例:**

```bash
uv pip install -e ".[web]"
uv run uvicorn src.household_mcp.server:app --port 8000
```

---

#### 💾 `db` - データベース連携

SQLAlchemy ORM を用いたデータベース永続化（将来の拡張向け）

**含まれるパッケージ:**

- `sqlalchemy >= 2.0.23` - ORM
- `alembic >= 1.12.1` - マイグレーション管理

**使用例:**

```bash
uv pip install -e ".[db]"
# SQLite/PostgreSQL への永続化機能（将来実装）
```

---

#### 🔐 `auth` - 認証機能

JWT・パスワード認証を実装し、API の保護・ユーザー認証に対応。

**含まれるパッケージ:**

- `passlib[bcrypt] >= 1.7.4` - パスワードハッシング
- `python-jose[cryptography] >= 3.3.0` - JWT 署名

**使用例:**

```bash
uv pip install -e ".[auth]"
# API 認証機能（将来実装）
```

---

#### ⚡ `io` - 非同期 I/O

非同期ファイル I/O・HTTP リクエスト機能を提供。

**含まれるパッケージ:**

- `aiofiles >= 23.2.1` - 非同期ファイル操作
- `httpx >= 0.25.2` - 非同期 HTTP クライアント

---

#### 📊 `logging` - 構造化ログ

JSON 形式の構造化ログを出力し、ログ解析・監視を容易にします。

**含まれるパッケージ:**

- `structlog >= 23.2.0` - ログ構造化フレームワーク

**インストールと使用例:**

```bash
# インストール
uv pip install -e ".[logging]"

# Pythonコードで使用
from household_mcp.logging_config import setup_logging, get_logger

# 標準ログ設定
setup_logging(level="INFO")

# 構造化ログ（コンソール出力）
setup_logging(level="DEBUG", use_structlog=True, json_format=False)

# 構造化ログ（JSON出力 - 本番環境推奨）
setup_logging(level="INFO", use_structlog=True, json_format=True)

# ロガーを取得
logger = get_logger(__name__)
logger.info("Application started", version="0.1.0", user_count=42)
```

---

#### 🎁 `full` - 完全インストール

すべてのオプション機能を有効化します。開発環境や試験用に推奨。

```bash
uv pip install -e ".[full]"
uv pip install -e ".[full,dev]"  # 開発環境 + 全機能
```

### Poetry を使用する場合

```bash
poetry install --with dev
# オプション機能: poetry install -E visualization
```

### pre-commit フックの有効化

```bash
pre-commit install
```

## 使用方法

### MCP / HTTP サーバーの起動（Monorepo 構成）

```bash
# 1) 依存インストール（backend/ で）
uv install --dev

# 2) オプション依存（API/可視化/DB が必要な場合）
uv pip install -e ".[web,streaming,visualization,db]"

# 3) API サーバー起動（backend/ にて）
uv run python -m uvicorn household_mcp.web.http_server:create_http_app \
  --factory --reload --host 0.0.0.0 --port 8000

# 代替: VS Code タスク
# - Start HTTP API Server（backend/）
# - Start Full Stack（API 8000 + Web 8080 を並列起動）
```

### 🌐 Webアプリケーションの使用

HTTPサーバと通信してインタラクティブに家計簿を操作できるWebアプリケーションが利用可能です。

#### 起動方法

1. **バックエンドサーバーの起動（backend/）**

```bash
# API サーバーを起動（ポート8000）
uv run python -m uvicorn household_mcp.web.http_server:create_http_app \
  --factory --reload --host 0.0.0.0 --port 8000
```

次に Web アプリを起動します：

```bash
# frontend ディレクトリに移動してHTTPサーバーを起動（ポート8080）
cd frontend
python3 -m http.server 8080
```

ブラウザでアクセス：

```text
http://localhost:8080
```

#### Webアプリの機能

- ✅ **年月選択** - ドロップダウンから期間を選択
- ✅ **グラフ表示** - 円グラフ、棒グラフ、折れ線グラフでデータを可視化
- ✅ **統計表示** - 総支出、取引件数、平均支出、最大支出
- ✅ **データテーブル** - 取引の詳細をテーブルで表示
- ✅ **検索・フィルタ** - 日付や内容で検索、カテゴリでフィルタリング
- ✅ **レスポンシブデザイン** - PC・タブレット・スマートフォン対応

詳細は [`frontend/README.md`](frontend/README.md) を参照してください。

### 重複レコード検出機能

AIエージェントとの会話を通じて、家計簿の重複取引を検出・解消できます。

#### 主な機能

- **自動検出**: 日付・金額・摘要の類似度から重複候補を自動抽出
- **対話的確認**: AIに「この取引は重複していますか？」と質問しながら検証
- **柔軟な判定**: ユーザーが最終的に確認・承認してから削除（誤削除防止）
- **統計表示**: 検出・解消した重複の件数や金額をレポート

#### MCPツール（会話方式）

```json
{
  "tool": "detect_duplicates",
  "arguments": {
    "date_tolerance_days": 3,
    "amount_tolerance_pct": 5
  }
}
```

**返却例:**

```json
{
  "success": true,
  "detected_count": 12,
  "message": "12件の重複候補を検出しました（信頼度80%以上）"
}
```

詳細は [`docs/duplicate_detection.md`](docs/duplicate_detection.md) を参照してください。

#### Webアプリでの使用方法

1. **メインページからアクセス**: 上部ナビゲーションの「重複検出」タブをクリック
2. **重複候補を確認**: 左側パネルにリスト表示される候補を確認
3. **詳細比較**: 右側パネルに2つの取引が並表示され、日付・金額・摘要を比較
4. **判定実行**: 「重複」「異なる」「スキップ」ボタンで判定
5. **結果確認**: 検出・解消した重複の統計を表示

### トレンド分析機能

収支の時系列推移を複数のグラフで可視化し、支出傾向を分析します。

#### 提供されるグラフ

- **月次推移**: 収入・支出・収支差額の3系列折れ線グラフ
- **累積収支**: 月ごとの累積収支を表示
- **カテゴリ別**: 主要カテゴリ（上位5）の月次推移を積み上げ棒グラフで表示

#### 使用方法

1. Webアプリの「トレンド分析」タブを開く
2. 期間を選択（プリセット: 直近3/6/12ヶ月、カスタム年月指定可）
3. グラフを切り替えて傾向を確認

### 画像生成機能

MCPツールから直接グラフ画像を生成して、AIエージェントに視覚的な洞察を提供できます。

#### インストール

画像生成機能を使用するには、`visualization` と `streaming` extras が必要です：

```bash
# 画像生成に必要な依存関係をインストール
uv pip install -e ".[visualization,streaming]"

# または、すべてのオプション機能を一括インストール
uv pip install -e ".[full]"
```

#### 日本語フォント設定

日本語ラベル付きグラフを生成するには、CJKフォントが必要です：

```bash
# fonts/ ディレクトリの作成（既に存在する場合はスキップ）
mkdir -p fonts

# Noto Sans CJK フォントのダウンロード（Ubuntu/Debian）
# システムに既にインストールされている場合は自動検出されます
sudo apt-get install fonts-noto-cjk

# または、プロジェクト内に配置
# fonts/NotoSansCJKjp-Regular.otf を配置
```

ChartGeneratorは以下の順序でフォントを自動検出します：

1. `fonts/NotoSansCJKjp-Regular.otf`（プロジェクトディレクトリ）
2. システムフォントディレクトリ（`/usr/share/fonts/`など）

#### 起動方法

##### 1. ストリーミングモード（推奨）

HTTPサーバーを起動して、生成した画像をブラウザから取得可能にします：

```bash
# HTTPストリーミングサーバーを起動（ポート8000）
uv run python -m uvicorn household_mcp.web.http_server:create_http_app --factory --reload --host 0.0.0.0 --port 8000

# MCP クライアントから接続（stdio）
# AIエージェントはMCP経由でツールを呼び出し、HTTPサーバーから画像を取得
```

##### 2. stdioモード（画像生成なし）

テキストベースのMCP通信のみ：

```bash
cd backend
uv run mcp install src/household_mcp/server.py
```

#### サポートされるグラフタイプ

- **円グラフ（pie）**: カテゴリ別支出割合
- **棒グラフ（bar）**: カテゴリ別比較
- **折れ線グラフ（line）**: 時系列トレンド
- **面グラフ（area）**: 累積トレンド

#### MCPツールからの使用例

Enhanced MCPツールを使用して、画像形式でレスポンスを取得：

```python
# 月次サマリーを画像で取得
{
  "tool": "enhanced_monthly_summary",
  "arguments": {
    "year": 2025,
    "month": 10,
    "output_format": "image",  # "text" または "image"
    "graph_type": "pie",       # "pie", "bar", "line", "area"
    "image_size": "800x600",   # WxH形式
    "image_format": "png"      # "png" または "svg"
  }
}

# レスポンス例
{
  "success": true,
  "type": "image",
  "url": "http://localhost:8000/api/charts/abc123def456",
  "chart_id": "abc123def456",
  "size_bytes": 55942
}

# カテゴリトレンドを画像で取得
{
  "tool": "enhanced_category_trend",
  "arguments": {
    "category": "食費",
    "start_month": "2024-01",
    "end_month": "2024-06",
    "output_format": "image"
  }
}
```

**HTTP エンドポイント経由でのアクセス**:

HTTPストリーミングモードで起動した場合、以下のエンドポイントが利用可能です：

```bash
# 画像取得（ストリーミング配信）
GET http://localhost:8000/api/charts/{chart_id}

# キャッシュ情報取得
GET http://localhost:8000/api/charts/{chart_id}/info

# キャッシュ統計
GET http://localhost:8000/api/cache/stats

# キャッシュクリア
DELETE http://localhost:8000/api/cache

# ヘルスチェック
GET http://localhost:8000/health
```

詳細は `docs/api.md` を参照してください。

### トレンド分析機能の詳細

#### 1. カテゴリトレンド分析（`get_category_trend`）

特定カテゴリの時系列推移を分析し、以下の指標を提供します：

**提供される指標:**

- 月次支出金額
- 前月比（MoM: Month over Month）
- 前年同月比（YoY: Year over Year）
- 12ヶ月移動平均

**テキスト出力例:**

```json
{
  "tool": "get_category_trend",
  "arguments": {
    "category": "食費",
    "start_month": "2024-01",
    "end_month": "2024-06"
  }
}

// レスポンス
{
  "category": "食費",
  "start_month": "2024-01",
  "end_month": "2024-06",
  "text": "食費の 2024年01月〜2024年06月 の推移です。...",
  "metrics": [
    {
      "month": "2024-01",
      "amount": -110942,
      "month_over_month": null,
      "year_over_year": -0.05,
      "moving_avg_12m": -108500
    },
    {
      "month": "2024-02",
      "amount": -123750,
      "month_over_month": 0.115,
      "year_over_year": 0.08,
      "moving_avg_12m": -109200
    }
    // ... 以下続く
  ]
}
```

**画像出力例:**

```json
{
  "tool": "get_category_trend",
  "arguments": {
    "category": "食費",
    "start_month": "2024-01",
    "end_month": "2024-06",
    "output_format": "image",
    "graph_type": "bar",
    "image_size": "1000x600"
  }
}

// レスポンス
{
  "success": true,
  "type": "image",
  "url": "http://localhost:8000/api/charts/abc123...",
  "cache_key": "abc123...",
  "media_type": "image/png",
  "alt_text": "食費のトレンド（bar）",
  "metadata": {
    "category": "食費",
    "start_month": "2024-01",
    "end_month": "2024-06",
    "graph_type": "bar",
    "image_size": "1000x600"
  }
}
```

#### 2. カテゴリ分析（`category_analysis`）

指定期間における全カテゴリの支出状況を一括分析します。

**提供される情報:**

- 期間内の総支出（カテゴリ別）
- 前月比の変化率
- 最大・最小支出月
- トップN支出カテゴリ

**使用例:**

```json
{
  "tool": "category_analysis",
  "arguments": {
    "start_month": "2024-01",
    "end_month": "2024-06",
    "top_n": 5
  }
}

// レスポンス
{
  "period": "2024-01 〜 2024-06",
  "total_expense": -850000,
  "categories": [
    {
      "name": "食費",
      "total": -350000,
      "avg_monthly": -58333,
      "month_over_month": 0.05,
      "max_month": {"month": "2024-05", "amount": -65000},
      "min_month": {"month": "2024-02", "amount": -52000}
    },
    // ... トップN件
  ],
  "top_categories": ["食費", "住居", "交通・通信", "日用品", "娯楽"]
}
```

#### 3. 月次サマリー画像生成（`get_monthly_household`）

特定月の支出構成を視覚化します。

**グラフタイプ:**

- `pie`: カテゴリ別支出割合（円グラフ）
- `bar`: カテゴリ別金額比較（棒グラフ）

**使用例:**

```json
{
  "tool": "get_monthly_household",
  "arguments": {
    "year": 2024,
    "month": 10,
    "output_format": "image",
    "graph_type": "pie",
    "image_size": "800x600"
  }
}

// レスポンス
{
  "success": true,
  "type": "image",
  "url": "http://localhost:8000/api/charts/def456...",
  "cache_key": "def456...",
  "media_type": "image/png",
  "alt_text": "2024年10月の支出構成（pie）",
  "metadata": {
    "year": 2024,
    "month": 10,
    "graph_type": "pie",
    "image_size": "800x600"
  }
}
```

### 利用可能な MCP リソース / ツール

#### リソース一覧

| 名称                            | 種別     | 説明                                 |
| ------------------------------- | -------- | ------------------------------------ |
| `data://category_hierarchy`     | Resource | 大項目→中項目のカテゴリ辞書          |
| `data://available_months`       | Resource | CSV から検出した利用可能年月         |
| `data://category_trend_summary` | Resource | 直近 12 か月のカテゴリ別トレンド情報 |

#### ツール一覧

| 名称                       | 説明                                                  | 出力形式        |
| -------------------------- | ----------------------------------------------------- | --------------- |
| `get_monthly_household`    | 指定年月の支出明細一覧と月次サマリー                  | テキスト        |
| `get_category_trend`       | カテゴリ別トレンド分析（前月比・前年比・移動平均）    | テキスト        |
| `category_analysis`        | カテゴリ別の期間分析（前月比・最大最小・トップN支出） | テキスト        |
| `find_categories`          | 利用可能なカテゴリ一覧を取得                          | テキスト        |
| `monthly_summary`          | 月次サマリ（収入・支出・カテゴリ別集計）              | テキスト        |
| `enhanced_monthly_summary` | 月次サマリー（画像対応）                              | テキスト / 画像 |
| `enhanced_category_trend`  | カテゴリトレンド（画像対応）                          | テキスト / 画像 |

### HTTP API エンドポイント

ストリーミングモードで起動した場合、以下のHTTP APIエンドポイントが利用可能です：

#### チャート画像配信

```text
GET /api/charts/{chart_id}
```

生成されたチャート画像をストリーミング配信します。

**パラメータ:**

- `chart_id` (path): チャートのキャッシュキー（MCPツールのレスポンスから取得）

**レスポンス:**

- `Content-Type: image/png`
- StreamingResponse（チャンク配信、8KB単位）

**使用例:**

```bash
# MCPツールで画像生成後、返されたURLを使用
curl http://localhost:8000/api/charts/abc123def456 -o chart.png
```

#### チャート情報取得

```text
GET /api/charts/{chart_id}/info
```

キャッシュされたチャートのメタデータを取得します。

**レスポンス:**

```json
{
  "chart_id": "abc123def456",
  "size_bytes": 55942,
  "media_type": "image/png"
}
```

#### キャッシュ統計

```text
GET /api/cache/stats
```

チャートキャッシュの統計情報を取得します。

**レスポンス:**

```json
{
  "current_size": 12,
  "max_size": 50,
  "ttl": 3600,
  "hit_rate": 0.75
}
```

#### キャッシュクリア

```text
DELETE /api/cache
```

すべてのキャッシュされたチャート画像をクリアします。

**レスポンス:**

```json
{
  "status": "success",
  "message": "Cache cleared"
}
```

#### ヘルスチェック

```text
GET /health
```

サーバーの稼働状況を確認します。

**レスポンス:**

```json
{
  "status": "healthy",
  "cache_size": 12
}
```

詳細は [`docs/api.md`](docs/api.md) を参照してください。

### 画像生成のパフォーマンスとキャッシング

画像生成機能は以下の最適化が施されています：

**パフォーマンス目標:**

- 初回生成: 3秒以内
- キャッシュヒット: 0.5秒以内
- メモリ使用量: 50MB以内（並行生成時）

**キャッシュ機構:**

生成された画像は自動的にキャッシュされ、同一パラメータでの再リクエスト時に即座に返されます。

```bash
# キャッシュ統計の確認
curl http://localhost:8000/api/cache/stats

# キャッシュクリア
curl -X DELETE http://localhost:8000/api/cache
```

**キャッシュキーの構成要素:**

- 画像タイプ（monthly, trend）
- 年月 / カテゴリ
- グラフタイプ（pie, bar, line, area）
- 画像サイズ
- フォーマット（png, svg）

### テスト・コード品質チェック

```bash
# backend ディレクトリで実行
cd backend

# テスト実行
uv run pytest

# カバレッジ付きテスト
uv run pytest --cov=src/household_mcp --cov-report=html

# コード品質チェック
uv run ruff format .            # コードフォーマット
uv run ruff check --select I --fix .  # インポート整理
uv run ruff check .             # リント
uv run bandit -r src/           # セキュリティスキャン

# すべてのチェックを一括実行（VS Code タスク）
# - All Checks（format/lint/tests/coverage）
```

### CI/CD パイプライン

本プロジェクトはGitHub Actionsで包括的なCIワークフローを実行しています：

**テストマトリクス:**

- Python 3.11, 3.12, 3.13, 3.14 での並列テスト
- pre-commit フック検証（markdownlint, black, flake8, mypy）
- カバレッジ収集（80%閾値）とCodecov連携

**Lintジョブ:**

- black, isort, flake8, mypy, bandit による静的解析
- Python 3.12環境での実行

**オプショナル依存テスト:**

- 7つのextrasグループ個別検証（visualization, streaming, web, db, auth, io, logging）
- スモークテスト（`-m "not slow" --maxfail=1`）

**完全インストールテスト:**

- `[full]` extra でのすべての依存関係同時インストール
- 完全なテストスイート実行

**ワークフロートリガー:**

- Push to `main`
- Pull Request to `main`
- 手動トリガー（`workflow_dispatch`）

詳細は [`.github/workflows/ci.yml`](.github/workflows/ci.yml) を参照してください。

**ローカルでの事前検証:**

```bash
# pre-commitフックのインストール
uv run pre-commit install

# すべてのファイルに対してpre-commitを実行
uv run pre-commit run --all-files
```

### 実用的な使用例

#### ケース1: 月次レポート生成

```python
# 先月の支出構成を円グラフで確認
from household_mcp.tools.enhanced_tools import enhanced_monthly_summary

result = enhanced_monthly_summary(
    year=2024,
    month=9,
    output_format="image",
    graph_type="pie",
    image_size="800x600"
)

print(f"画像URL: {result['url']}")
print(f"キャッシュキー: {result['cache_key']}")
```

#### ケース2: カテゴリ別トレンド分析

```python
# 食費の半年トレンドを棒グラフで可視化
from household_mcp.tools.enhanced_tools import enhanced_category_trend

result = enhanced_category_trend(
    category="食費",
    start_month="2024-04",
    end_month="2024-09",
    output_format="image",
    graph_type="bar",
    image_size="1000x600"
)

# 画像をブラウザで確認
# ブラウザで result['url'] にアクセス
```

#### ケース3: 全カテゴリ分析

```python
# 直近3ヶ月の全カテゴリ支出状況を分析
from household_mcp.tools.trend_tool import category_analysis

result = category_analysis(
    start_month="2024-07",
    end_month="2024-09",
    top_n=10
)

print(f"期間総支出: {result['total_expense']}円")
for cat in result['top_categories']:
    print(f"  - {cat['name']}: {cat['total']}円")
```

### テスト

```bash
uv run pytest
```

カバレッジ閾値 80% を満たすと成功です。

## 日本語フォント設定

グラフ生成機能で日本語（漢字・カナ）を正しく描画するには、日本語フォントの設定が必要です。

### フォント配置（推奨）

プロジェクトの `fonts/` ディレクトリに Noto Sans CJK フォントを配置します：

```bash
# Debian/Ubuntu の場合
sudo apt-get install fonts-noto-cjk
cp /usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc fonts/

# または、直接ダウンロード
wget https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansCJKjp-Regular.otf -O fonts/NotoSansCJKjp-Regular.otf
```

詳細な手順は `fonts/README.md` を参照してください。

### フォント検出の優先順位

`ChartGenerator` は以下の順序でフォントを検出します：

1. **ローカル fonts/ ディレクトリ**: プロジェクト内の `fonts/` 配下
2. **プラットフォーム固有パス**:
   - Linux: `/usr/share/fonts/opentype/noto/`, `/usr/share/fonts/truetype/noto/`
   - macOS: `/System/Library/Fonts/`
   - Windows: `C:/Windows/Fonts/`
3. **matplotlib font_manager**: システムにインストールされた全フォントから検索

### フォント未設定時の動作

フォントが検出できない場合でもグラフ生成は可能ですが、日本語が文字化けする可能性があります。
画像生成機能を使用する場合は、必ず日本語フォントを配置してください。

### システムフォントのインストール（参考）

```bash
# Debian/Ubuntu
sudo apt-get update && sudo apt-get install -y fonts-noto-cjk

# Arch Linux
sudo pacman -Sy --noconfirm noto-fonts-cjk

# Alpine Linux
sudo apk add --no-cache font-noto-cjk

# macOS (Homebrew)
brew install font-noto-sans-cjk-jp

# インストール後、フォントキャッシュを更新
fc-cache -fv
```

## デプロイメント

Docker Compose を使用した簡単なデプロイメントをサポートしています。

### クイックスタート（開発環境）

```bash
# 環境変数の設定
cp .env.example .env

# 開発環境を起動
./scripts/start-dev.sh
```

アクセス:

- **フロントエンド**: <http://localhost:8080>
- **バックエンド API**: <http://localhost:8000>
- **API ドキュメント**: <http://localhost:8000/docs>

### 本番環境のデプロイ

```bash
# 本番環境を起動（nginx リバースプロキシ含む）
./scripts/start-prod.sh
```

アクセス:

- **メインURL**: <http://localhost>
- **API ドキュメント**: <http://localhost/api/docs>

### サービス管理

```bash
# サービスの停止
./scripts/stop.sh

# ログの確認
docker compose logs -f

# サービスの再起動
docker compose restart
```

詳細なデプロイメント手順、設定、トラブルシューティングについては [デプロイメントガイド](docs/deployment.md) を参照してください。

## ドキュメント

- [利用ガイド](docs/usage.md) - 詳細な使用方法とパラメータ説明
- [サンプル会話例](docs/examples.md) - LLMクライアントでの実践的なプロンプト例
- [FAQ](docs/FAQ.md) - よくある質問とトラブルシューティング
- [API リファレンス](docs/api.md) - HTTPエンドポイント仕様
- [デプロイメントガイド](docs/deployment.md) - Docker Composeを使用したデプロイメント手順

## 開発

このプロジェクトは [Kiro's Spec-Driven Development](https://github.com/kiro-dev) に従って開発されています：

- [`requirements.md`](requirements.md) - 要件定義
- [`design.md`](design.md) - 技術設計
- [`tasks.md`](tasks.md) - 実装タスク

### バックエンド開発

```bash
# ディレクトリ移動
cd backend

# 依存関係のインストール
uv install --dev

# テストの実行
uv run pytest

# カバレッジ付きテスト
uv run pytest --cov=src --cov-report=html

# Lint/Format
uv run black .
uv run isort .
uv run flake8
uv run mypy src/
```

### フロントエンド開発

```bash
# ディレクトリ移動
cd frontend

# 依存関係のインストール
npm install

# テストの実行
npm test

# テストのwatch mode
npm run test:watch

# カバレッジ付きテスト
npm run test:coverage

# Lint/Format
npm run lint
npm run format
```

詳細なフロントエンドテストガイドは [frontend/tests/README.md](frontend/tests/README.md) を参照してください。

## MCP ツール実行 UI

家計簿アプリには、ブラウザから対話的に MCP ツールを実行できるユーザーインターフェースが組み込まれています。

### アクセス方法

1. **バックエンド API を起動**

   ```bash
   cd backend
   uv run uvicorn household_mcp.web.http_server:app --reload --host 0.0.0.0 --port 8000
   ```

2. **フロントエンドを起動**

   ```bash
   cd frontend
   python -m http.server 8080
   ```

3. **ブラウザで開く**

   ```url
   http://localhost:8080/mcp-tools.html
   ```

### 利用可能なツール

| ツール名                     | 説明                   | パラメータ                                               |
| ---------------------------- | ---------------------- | -------------------------------------------------------- |
| **enhanced_monthly_summary** | 指定年月の家計簿集計   | `year` (int), `month` (int)                              |
| **enhanced_category_trend**  | カテゴリ別トレンド分析 | `category` (str), `start_month` (str), `end_month` (str) |
| **detect_duplicates**        | 重複取引検出           | `threshold` (float, 0-1)                                 |
| **get_duplicate_candidates** | 重複候補をリスト表示   | なし                                                     |
| **confirm_duplicate**        | 重複を確認して解消     | `id1` (int), `id2` (int)                                 |

### 機能

- **ツールギャラリー**: カード形式で全ツールを表示
- **パラメータ入力**: モーダルダイアログで必須/オプションパラメータを入力
- **リアルタイム実行**: ツール実行後、JSON/テーブル形式で結果を表示
- **エラーハンドリング**: 実行エラーをわかりやすく表示
- **アクセシビリティ**: ARIA ラベル、キーボードナビゲーション対応
- **レスポンシブデザイン**: モバイル(480px) / タブレット(768px) / デスクトップ対応

### キーボード操作

| キー          | 動作                         |
| ------------- | ---------------------------- |
| **Tab**       | フォーカスを次の要素に移動   |
| **Shift+Tab** | フォーカスを前の要素に移動   |
| **Esc**       | モーダルダイアログを閉じる   |
| **Enter**     | ボタンを実行（フォーカス時） |

### カスタマイズ

新しいツールを追加する場合は、`backend/src/household_mcp/web/http_server.py` の `TOOL_DEFINITIONS` リストに定義を追加してください：

```python
{
    "name": "tool_identifier",
    "display_name": "ツール表示名",
    "description": "ツール説明",
    "category": "分析",
    "parameters": {
        "required": [
            {
                "name": "param1",
                "type": "integer",  # or "number", "string", "date"
                "description": "パラメータ説明"
            }
        ],
        "optional": []
    }
}
```

## ライセンス

MIT License
