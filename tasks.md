# 家計簿分析 MCP サーバー タスク計画

- **バージョン**: 0.2.0
- **更新日**: 2025-10-03
- **対象設計**: [design.md](./design.md)
- **対象要件**: FR-001〜FR-003, NFR-001〜NFR-004

---

## フェーズ0: 既存基盤の棚卸し (Day 1)

- [x] **TASK-000**: 現行コード/データの確認
  - [x] `src/server.py` の既存 MCP リソース/ツールの挙動を確認（FR-001）
  - [x] `data/` 配下 CSV の構造と列揺れの差異を棚卸し（FR-001）
  - [x] 既存ユーティリティの再利用可否を評価（NFR-003）
    - DataLoader リファクタ & クラス化済み
    - レガシー `validators.py` / `data_tools.py` 削除済み（クリーンアップ）

---

## フェーズ1: インフラ・ユーティリティ整備 (Week 1)

- [x] **TASK-101**: 例外クラスとロギング基盤の整備（NFR-003）
  - [x] `src/household_mcp/exceptions.py` を新設し、`HouseholdMCPError`, `ValidationError`, `DataSourceError`, `AnalysisError` 実装
  - [ ] ログフォーマッタ設定（未着手 / ロギング extra に移行予定）

- [x] **TASK-102**: データ読み込みユーティリティの強化（FR-001, NFR-002）
  - [x] 列名マッピングと Categorical 型設定を実装（`_normalize_columns`）
  - [x] バルク読み込みヘルパー `load_many` 追加
  - [x] 欠損/対象外フィルタリング実装（`_post_process`）
  - [x] 月次キャッシュ + mtime 検知機構追加（拡張: `cache_stats` / hits & misses）

- [x] **TASK-103**: フォーマットユーティリティの追加（NFR-001）
  - [x] `format_currency`, `format_percentage`, 集計レスポンス整形関数実装
  - [x] 例外ハンドリングによるフォールバック（`format_percentage` の NaN → N/A）

- [x] **TASK-104**: クエリ解析ユーティリティの追加（FR-002, FR-003）
  - [x] `resolve_trend_query` による期間 & カテゴリ解釈
  - [x] 利用可能月のソート/キー化ユーティリティ
  - [x] 検証失敗時 `ValidationError` 送出を確認

---

## フェーズ2: トレンド分析コア実装 (Week 2)

- [ ] **TASK-201**: `CategoryTrendAnalyzer` の実装（FR-001, NFR-002）
  - [ ] `src/household_mcp/analysis/trends.py` を新設
  - [ ] 月次支出集計 + 指標（前月比/前年比/12か月移動平均）の計算
  - [ ] データ不足時の `AnalysisError` ハンドリング

- [ ] **TASK-202**: トレンド結果キャッシュ（NFR-002, NFR-003）
  - [ ] 分析結果を `functools.lru_cache` 等でメモ化
  - [ ] CSV 更新検知（ファイル更新時のキャッシュ無効化ポリシー）を実装

- [ ] **TASK-203**: レスポンスフォーマットの整備（FR-003, NFR-001）
  - [ ] `TrendResponseFormatter` でランキング/注釈テキストを生成
  - [ ] データ不足メッセージや N/A 表記の統一化

---

## フェーズ3: MCP リソース・ツール追加 (Week 3)

- [ ] **TASK-301**: `data://category_trend_summary` リソース実装（FR-001）
  - [ ] 直近 12 か月の指標サマリ辞書を返却
  - [ ] リクエスト毎に最新データを判定し、キャッシュ利用を制御

- [ ] **TASK-302**: `get_category_trend` ツール実装（FR-002, FR-003）
  - [ ] 入力検証〜解析〜フォーマットまでのオーケストレーションを構築
  - [ ] カテゴリ未指定時に上位カテゴリを返すフォールバックを実装
  - [ ] MCP エラーレスポンスの整備（NFR-003）

- [ ] **TASK-303**: サーバー登録処理の更新（FR-001〜FR-003）
  - [ ] `src/server.py` で新リソース/ツールを登録
  - [ ] 既存リソースドキュメントの整合性確認

---

## フェーズ4: テスト & 品質ゲート (Week 4)

- [ ] **TASK-401**: 単体テスト追加（TS-001〜TS-006）
  - [ ] `tests/unit/test_dataloader.py` に読み込みケースを追加
  - [ ] `tests/unit/analysis/test_trends.py` で指標計算結果を検証
  - [ ] `tests/unit/tools/test_get_category_trend.py` で入力バリエーションを網羅

- [ ] **TASK-402**: 統合テスト整備（TS-007〜TS-009）
  - [ ] `tests/integration/test_trend_pipeline.py` で E2E フローを検証
  - [ ] データ不足・カテゴリ未指定などのエッジケース確認

- [ ] **TASK-403**: 自動化と品質ゲート（NFR-002, NFR-003）
  - [ ] CI で `uv run pytest` を実行するワークフローを準備
  - [ ] 主要関数に型ヒントと docstring を追加

### 追加テスト進捗
- [x] DataLoader キャッシュ差分テスト (`test_cache_behaviour`)
- [x] キャッシュ統計テスト (`test_loader_cache_stats`) 追加（ヒット/ミス/リセット）
- [x] 異常系（欠損列/カテゴリ欠如/無効ディレクトリ）テスト拡張

---

## フェーズ5: ドキュメント & 運用準備 (Week 5)

- [ ] **TASK-501**: ドキュメント更新
  - [ ] `README.md` にトレンド分析ツールの利用方法を追記
  - [ ] `requirements.md` / `design.md` の変更点を CHANGELOG に連携

- [ ] **TASK-502**: サンプル会話・FAQ 整備
  - [ ] LLM クライアント向けのプロンプト例を追加
  - [ ] 発生しやすいエラーと対処法のまとめ

- [ ] **TASK-503**: 検収手順の確立
  - [ ] UAT チェックリストを作成し、受入条件に紐付け
  - [ ] デモ用シナリオデータの準備

---

## マイルストーン確認

| マイルストーン | 目標週 | 完了条件 |
| --- | --- | --- |
| MS-1 | Week 1 | データ読み込み/フォーマットユーティリティの整備完了（TASK-101〜104） |
| MS-2 | Week 2 | トレンド分析コアとキャッシュ機構が動作（TASK-201〜203） |
| MS-3 | Week 3 | 新リソース/ツールが MCP 経由で利用可能（TASK-301〜303） |
| MS-4 | Week 4 | 単体・統合テストがグリーン（TASK-401〜403） |
| MS-5 | Week 5 | ドキュメントと UAT 手順が揃い受入準備完了（TASK-501〜503） |

---

## チェックリスト (継続)

- [ ] CSV 更新時のキャッシュ無効化が想定通り動くか定期的に確認（NFR-002）
- [ ] 数値フォーマット仕様の一貫性を維持（NFR-001）
- [ ] 例外メッセージがユーザーにとって分かりやすいかレビュー（NFR-003）
- [ ] データはすべてローカル処理で完結しているか確認（NFR-004）

---

## 追加タスク（メンテナンス / 改善）

- [ ] **TASK-M01**: 依存最小化ポリシー文書化（README に optional extras 追記）
- [ ] **TASK-M02**: `logging` extra 選択時の構成ヘルパー追加（structlog 初期化）
- [ ] **TASK-M03**: Analyzer 側キャッシュ統計インターフェース統一 (`CategoryTrendAnalyzer.cache_stats`) 追加
- [ ] **TASK-M04**: 例外メッセージ多言語方針（現在: 日/英 混在）整理
- [ ] **TASK-M05**: CI ワークフロー (lint + test + coverage) 追加

---

## 進捗ログ

| 日付 | 内容 |
| ---- | ---- |
| 2025-10-03 | DataLoader リファクタ・例外統一・追加カバレッジテスト |
| 2025-10-04 | レガシーコード削除 / 依存最小化 / キャッシュ統計追加 / tasks.md 更新 |

---

**作成日**: 2025年10月03日  
**プロジェクトマネージャー**: GitHub Copilot (AI assistant)
