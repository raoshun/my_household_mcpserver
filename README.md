# Household MCP Server

家計簿CSVをインメモリで分析し、AIエージェントとの自然言語会話に必要な情報を提供する MCP（Model Context Protocol）サーバーです。

## 概要

このプロジェクトは、ローカルの家計簿CSV（`data/` 配下）を pandas で分析し、AI エージェントからの自然言語リクエストに応答する MCP サーバーを提供します。ユーザーは複雑なクエリ言語を学ぶことなく、日常会話で家計データの洞察を得ることができます。

## 主な機能

- **自然言語インターフェース**: 日本語でカテゴリ別・期間別の支出推移を確認
- **トレンド分析**: 月次集計、前月比・前年同月比・12か月移動平均の計算
- **カテゴリハイライト**: 指定期間で支出が大きいカテゴリを自動抽出
- **ローカル完結設計**: CSV ファイルをローカルで読み込み、外部通信なしで解析

## 要件

- Python 3.12 以上（`uv` を推奨）
- 家計簿 CSV ファイル（`data/収入・支出詳細_YYYY-MM-DD_YYYY-MM-DD.csv` 形式）

## インストール

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

本プロジェクトは、依存関係の軽量化のため、追加機能は **optional dependencies** として提供されます。
必要な機能に応じて、以下から選択してインストールしてください。

#### 機能別インストールガイド

| 機能 | オプション | 用途 | 依存パッケージ数 |
|------|---------|------|---|
| **MCP サーバー基本** | なし | CSV 読み込み・MCP リソース/ツール提供 | 4 個 |
| **画像生成** | `visualization` | グラフ・チャート生成（PNG/SVG） | +3 個 |
| **HTTP ストリーミング** | `streaming` | FastAPI 経由の画像配信 | +3 個 |
| **Web API** | `web` | REST API エンドポイント | +4 個 |
| **データベース連携** | `db` | SQLite/PostgreSQL への永続化 | +2 個 |
| **認証** | `auth` | JWT・パスワード認証機能 | +2 個 |
| **非同期 I/O** | `io` | aiofiles・httpx 対応 | +2 個 |
| **構造化ログ** | `logging` | structlog による詳細ログ出力 | +1 個 |
| **すべて** | `full` | 全機能を有効化 | +17 個 |

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

**使用例:**

```bash
uv pip install -e ".[logging]"
# 環境変数で有効化: HOUSEHOLD_MCP_LOGGING=structlog
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

### MCP サーバーの起動

```bash
# 標準 MCP サーバー起動（stdio モード）
python -m src.server

# HTTPストリーミングモード（画像配信対応）
# 注: streaming または web extras のインストールが必要
uv pip install -e ".[streaming]"
python -m src.server --transport streamable-http --port 8000

# または uvicorn で直接起動
uv run uvicorn household_mcp.http_server:app --host 0.0.0.0 --port 8000
```

### 画像生成機能（オプション）

画像生成機能を使用するには、追加の依存関係とフォント設定が必要です：

```bash
# 画像生成に必要な依存関係をインストール
uv pip install -e ".[visualization]"

# 日本語フォントを配置
# fonts/ ディレクトリに Noto Sans CJK を配置
# 詳細は「日本語フォント設定」セクションを参照
```

**サポートされるグラフタイプ**:

- 円グラフ（pie）: カテゴリ別支出割合
- 棒グラフ（bar）: カテゴリ別比較
- 折れ線グラフ（line）: 時系列トレンド
- 面グラフ（area）: 累積トレンド

**MCP ツールからの使用例**:

```python
# 月次サマリーを画像で取得
{
  "tool": "get_monthly_household",
  "arguments": {
    "year": 2025,
    "month": 10,
    "output_format": "image",
    "graph_type": "pie",
    "image_size": "800x600",
    "image_format": "png"
  }
}

# レスポンス
{
  "success": true,
  "type": "image",
  "url": "http://localhost:8000/api/charts/abc123...",
  "metadata": {
    "graph_type": "pie",
    "format": "png",
    "size": "800x600",
    "cache_key": "abc123..."
  }
}

# カテゴリトレンドを画像で取得
{
  "tool": "get_category_trend",
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

### 利用可能な MCP リソース / ツール

| 名称                            | 種別     | 説明                                       |
| ------------------------------- | -------- | ------------------------------------------ |
| `data://category_hierarchy`     | Resource | 大項目→中項目のカテゴリ辞書                |
| `data://available_months`       | Resource | CSV から検出した利用可能年月               |
| `data://category_trend_summary` | Resource | 直近 12 か月のカテゴリ別トレンド情報       |
| `get_monthly_household`         | Tool     | 指定年月の支出明細一覧                     |
| `get_category_trend`            | Tool     | 指定カテゴリ or 上位カテゴリのトレンド解説 |
| `category_analysis`             | Tool     | カテゴリ別の期間分析（前月比・最大最小）    |
| `find_categories`               | Tool     | 利用可能なカテゴリ一覧を取得               |
| `monthly_summary`               | Tool     | 月次サマリ（収入・支出・カテゴリ別集計）    |

### テスト・コード品質チェック

```bash
# テスト実行
uv run pytest

# カバレッジ付きテスト
uv run pytest --cov=src/household_mcp --cov-report=html

# コード品質チェック
uv run black .          # コードフォーマット
uv run isort .          # インポート整理
uv run flake8           # リント
uv run mypy src/        # 型チェック
uv run bandit -r src/   # セキュリティスキャン

# すべてのチェックを一括実行
uv run task all-checks  # ※ tasks.json に定義
```

### サンプル応答

```json
{
  "category": "食費",
  "start_month": "2025-06",
  "end_month": "2025-07",
  "text": "食費の 2025年06月〜2025年07月 の推移です。...",
  "metrics": [
    {"month": "2025-06", "amount": -62500, "month_over_month": null},
    {"month": "2025-07", "amount": -58300, "month_over_month": -0.067}
  ]
}
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

## 開発

このプロジェクトは [Kiro's Spec-Driven Development](https://github.com/kiro-dev) に従って開発されています：

- [`requirements.md`](requirements.md) - 要件定義
- [`design.md`](design.md) - 技術設計
- [`tasks.md`](tasks.md) - 実装タスク

## ライセンス

MIT License
