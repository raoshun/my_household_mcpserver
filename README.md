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

```bash
# 推奨: uv を用いたインストール
uv pip install -e ".[dev]"

# 必要に応じてオプション機能を追加
uv pip install -e ".[web,viz,db,auth,io,logging]"
# 例: Web API 機能を使う場合
uv pip install -e ".[web]"
# 例: グラフ描画や可視化を使う場合
uv pip install -e ".[viz]"
# 例: DB連携や認証が必要な場合
uv pip install -e ".[db,auth]"
# 例: ロギング強化（structlog）
uv pip install -e ".[logging]"

# 代替: Poetry を使用する場合
# poetry install --with dev

# pre-commit フックの有効化
pre-commit install
```

## 使用方法

### MCP サーバーの起動

```bash
# MCP サーバー起動
python -m src.server

# テスト実行
uv run pytest  # または poetry run pytest

# コード品質チェック例
uv run black .
uv run isort .
uv run flake8
uv run mypy src/
```

### 利用可能な MCP リソース / ツール

| 名称                            | 種別     | 説明                                       |
| ------------------------------- | -------- | ------------------------------------------ |
| `data://category_hierarchy`     | Resource | 大項目→中項目のカテゴリ辞書                |
| `data://available_months`       | Resource | CSV から検出した利用可能年月               |
| `data://category_trend_summary` | Resource | 直近 12 か月のカテゴリ別トレンド情報       |
| `get_monthly_household`         | Tool     | 指定年月の支出明細一覧                     |
| `get_category_trend`            | Tool     | 指定カテゴリ or 上位カテゴリのトレンド解説 |

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

## 開発

このプロジェクトは [Kiro's Spec-Driven Development](https://github.com/kiro-dev) に従って開発されています：

- [`requirements.md`](requirements.md) - 要件定義
- [`design.md`](design.md) - 技術設計
- [`tasks.md`](tasks.md) - 実装タスク

## ライセンス

MIT License
