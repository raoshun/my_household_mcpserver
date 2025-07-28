# Household MCP Server

家計簿分析をAIエージェントとの自然言語会話で行うためのMCP（Model Context Protocol）サーバーです。

## 概要

このプロジェクトは、家計簿データの分析をAIエージェントとの自然言語会話で実現するMCPサーバーを提供します。ユーザーは複雑なクエリ言語を学ぶことなく、日常会話で家計データの洞察を得ることができます。

## 主な機能

- **自然言語インターフェース**: 日本語での家計分析
- **データ管理**: 取引データ、カテゴリー、アカウントの管理
- **分析機能**: トレンド分析、異常検知、予算管理
- **レポート生成**: 月次・年次レポートの自動生成
- **プライバシー保護**: ローカル処理によるデータセキュリティ

## 要件

- Python 3.11以上
- SQLite（デフォルト）またはPostgreSQL

## インストール

```bash
# 開発環境のセットアップ
make setup

# または手動で
pip install -e ".[dev]"
pre-commit install
```

## 使用方法

```bash
# 開発サーバーの起動
make run-dev

# テストの実行
make test

# コード品質チェック
make check-all
```

## 開発

このプロジェクトは [Kiro's Spec-Driven Development](https://github.com/kiro-dev) に従って開発されています：

- [`requirements.md`](requirements.md) - 要件定義
- [`design.md`](design.md) - 技術設計
- [`tasks.md`](tasks.md) - 実装タスク

## ライセンス

MIT License
