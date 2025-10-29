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
# 推奨: uv を用いた基本インストール
uv pip install -e "."

# 開発環境（テスト・lint含む）
uv pip install -e ".[dev]"
```

### オプション機能の追加

画像生成やHTTPストリーミングなど、追加機能ごとに依存関係を選択できます：

```bash
# 画像生成機能（matplotlib, pillow）
uv pip install -e ".[visualization]"

# HTTPストリーミング（FastAPI, uvicorn, cachetools）
uv pip install -e ".[streaming]"

# Web API機能
uv pip install -e ".[web]"

# すべての機能を含む完全インストール
uv pip install -e ".[full]"

# その他のオプション
uv pip install -e ".[db]"        # DB連携（SQLAlchemy）
uv pip install -e ".[auth]"      # 認証機能
uv pip install -e ".[io]"        # 非同期I/O
uv pip install -e ".[logging]"   # 構造化ログ（structlog）
```

### 推奨セットアップ（画像生成機能込み）

```bash
# 画像生成とHTTPストリーミング機能を含む開発環境
uv pip install -e ".[full,dev]"

# 日本語フォントの配置（必須）
# fonts/ ディレクトリに Noto Sans CJK フォントを配置
# 詳細は「日本語フォント設定」セクションを参照
```

### Poetry を使用する場合

```bash
poetry install --with dev
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
# ※ 現在実装中 - TASK-603 完了後に利用可能
# python -m src.server --transport streamable-http --port 8080
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

**使用例**（実装予定 - TASK-604）:
```python
# MCPツールから画像生成をリクエスト
{
  "tool": "get_monthly_household",
  "arguments": {
    "year": 2025,
    "month": 10,
    "output_format": "image",
    "graph_type": "pie",
    "image_size": "800x600"
  }
}
```

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
