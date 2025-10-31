# 家計簿分析 MCP サーバー タスク計画

- **バージョン**: 0.5.0
- **更新日**: 2025-11-01
- **対象設計**: [design.md](./design.md)
- **対象要件**: FR-001〜FR-018, NFR-001〜NFR-013

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

- [x] **TASK-201**: `CategoryTrendAnalyzer` の実装（FR-001, NFR-002）
  - [x] `src/household_mcp/analysis/trends.py` を新設
  - [x] 月次支出集計 + 指標（前月比/前年比/12か月移動平均）の計算
  - [x] データ不足時の `AnalysisError` ハンドリング

- [x] **TASK-202**: トレンド結果キャッシュ（NFR-002, NFR-003）
  - [x] 集計DataFrameの署名ベースキャッシュを実装（CSV mtime で無効化）
  - [x] ローダの月次キャッシュと併用

- [x] **TASK-203**: レスポンスフォーマットの整備（FR-003, NFR-001）
  - [x] `format_category_trend_response` / `trend_metrics_to_dict` を実装
  - [x] N/A 表記の統一（NaN/None）

---

## フェーズ3: MCP リソース・ツール追加 (Week 3)

- [x] **TASK-301**: `data://category_trend_summary` リソース実装（FR-001）
  - [x] 直近 12 か月の指標サマリ辞書を返却
  - [x] リクエスト毎に最新データを判定し、キャッシュ利用を制御

- [x] **TASK-302**: `get_category_trend` ツール実装（FR-002, FR-003）
  - [x] 入力検証〜解析〜フォーマットまでのオーケストレーションを構築
  - [x] カテゴリ未指定時に上位カテゴリを返すフォールバックを実装
  - [x] MCP エラーレスポンスの整備（NFR-003）

- [x] **TASK-303**: サーバー登録処理の更新（FR-001〜FR-003）
  - [x] `src/server.py` で新リソース/ツールを登録
  - [x] 既存リソースドキュメントの整合性確認

---

## フェーズ4: テスト & 品質ゲート (Week 4)

- [x] **TASK-401**: 単体テスト追加（TS-001〜TS-006）
  - [x] `tests/unit/test_dataloader.py` に読み込みケースを追加（8テスト：エラー処理、フィルタリング、検証）
  - [x] `tests/unit/analysis/test_trends.py` で指標計算結果を検証（既存）
  - [x] `tests/unit/tools/test_get_category_trend.py` を追加（基本ケース）
  - カバレッジ向上: `dataloader.py` 81%, `trends.py` 86%, `trend_tool.py` 84%
  - 実装日: 2025-11-01

- [x] **TASK-402**: 統合テスト整備（TS-007〜TS-009）
  - [x] `tests/integration/test_trend_pipeline.py` で E2E フローを検証（8テスト）
  - [x] エンドツーエンドパイプライン（resolve_trend_query → analyzer → formatter）
  - [x] エラーケース: 存在しないカテゴリ、不正な日付範囲
  - [x] エッジケース: カテゴリ未指定（全カテゴリ）、単月分析、キャッシュ動作
  - [x] 複数月集計と前年同月比計算の検証
  - 実装日: 2025-11-01

- [x] **TASK-403**: 自動化と品質ゲート（NFR-002, NFR-003）
  - [x] All Checks タスクが PASS（format/isort/flake8/mypy/bandit/pytest）

### 追加テスト進捗

- [x] DataLoader キャッシュ差分テスト (`test_cache_behaviour`)
- [x] キャッシュ統計テスト (`test_loader_cache_stats`) 追加（ヒット/ミス/リセット）
- [x] 異常系（欠損列/カテゴリ欠如/無効ディレクトリ）テスト拡張

---

## フェーズ5: ドキュメント & 運用準備 (Week 5)

- [x] **TASK-501**: ドキュメント更新
  - [x] `README.md` にトレンド分析ツールの利用方法を追記
  - [x] 画像生成機能の詳細セクション追加（Phase 6）
  - [x] HTTP APIエンドポイント完全ドキュメント化（Phase 6）
  - [x] Webアプリケーション使用方法追加（Phase 7）
  - [x] 依存関係最小化ポリシー文書化（TASK-M01）
  - [x] CI/CDパイプライン説明追加（TASK-M05）
  - [x] `requirements.md` / `design.md` の変更点を CHANGELOG に連携
  - 更新日: 2025-11-01（Phase 6/7機能反映）

- [x] **TASK-502**: サンプル会話・FAQ 整備
  - [x] `docs/examples.md` - LLMクライアント向けプロンプト例（14例）
    - 基本的な会話パターン（月次確認、トレンド、比較）
    - 画像生成を活用した会話（グラフ表示、複数カテゴリ比較）
    - 高度な分析（予測、異常検出、カテゴリ分析）
    - Webアプリケーション使用例（例13-14）
    - MCP + Webアプリ併用ワークフロー
    - エラーハンドリング例（4パターン）
  - [x] `docs/FAQ.md` - よくある質問（48項目）
    - インストールと環境設定（Q1-Q4）
    - データとCSV（Q5-Q8）
    - 画像生成（Q9-Q12）
    - トレンド分析（Q13-Q20）
    - MCPツール（Q21-Q27）
    - 開発とカスタマイズ（Q28-Q30）
    - トラブルシューティング（Q31-Q38）
    - セキュリティ（Q39-Q40）
    - Webアプリケーション（Q41-Q48、Phase 7反映）
  - [x] 発生しやすいエラーと対処法のまとめ
  - 更新日: 2025-11-01（Webアプリ Q&A追加）

- [x] **TASK-503**: 検収手順の確立
  - [x] UAT チェックリストを作成し、受入条件に紐付け
  - [x] デモ用シナリオデータの準備

---

## マイルストーン確認

| マイルストーン | 目標週 | 完了条件                                                             |
| -------------- | ------ | -------------------------------------------------------------------- |
| MS-1           | Week 1 | データ読み込み/フォーマットユーティリティの整備完了（TASK-101〜104） |
| MS-2           | Week 2 | トレンド分析コアとキャッシュ機構が動作（TASK-201〜203）              |
| MS-3           | Week 3 | 新リソース/ツールが MCP 経由で利用可能（TASK-301〜303）              |
| MS-4           | Week 4 | 単体・統合テストがグリーン（TASK-401〜403）                          |
| MS-5           | Week 5 | ドキュメントと UAT 手順が揃い受入準備完了（TASK-501〜503）           |

---

## チェックリスト (継続)

- [ ] CSV 更新時のキャッシュ無効化が想定通り動くか定期的に確認（NFR-002）
- [ ] 数値フォーマット仕様の一貫性を維持（NFR-001）
- [ ] 例外メッセージがユーザーにとって分かりやすいかレビュー（NFR-003）
- [ ] データはすべてローカル処理で完結しているか確認（NFR-004）

---

## 追加タスク（メンテナンス / 改善）

- [x] **TASK-M01**: 依存最小化ポリシー文書化（README に optional extras 追記）
  - [x] README.mdに依存最小化ポリシーセクション追加
  - [x] コア機能vs拡張機能の設計原則を明文化
  - [x] 必須依存4パッケージのみで基本機能動作を保証
  - 実装日: 2025-11-01

- [x] **TASK-M02**: `logging` extra 選択時の構成ヘルパー追加（structlog 初期化）
  - [x] `src/household_mcp/logging_config.py` 新規作成
  - [x] `setup_logging()` 関数実装（標準/structlog切り替え、JSON形式対応）
  - [x] `get_logger()` 関数実装（structlog/標準loggingの自動選択）
  - [x] structlog未インストール時の適切なフォールバック機能
  - [x] 単体テスト追加（4 passed, 2 skipped）
  - [x] README.mdに使用例を記載
  - 実装日: 2025-11-01

- [x] **TASK-M03**: Analyzer 側キャッシュ統計インターフェース統一 (`CategoryTrendAnalyzer.cache_stats`) 追加
  - [x] `cache_stats()` メソッド実装（詳細な統計情報を返却）
  - [x] 返却情報: size（キャッシュエントリ数）、entries（月範囲リスト）、total_months（ユニーク月数）
  - [x] 既存の `cache_size()` と `clear_cache()` を補完する統一インターフェース
  - [x] 単体テスト追加（test_cache_stats: 空キャッシュ、単一エントリ、複数エントリのテスト）
  - 用途: キャッシュ効果測定、メモリ使用量監視、デバッグ・パフォーマンスチューニング
  - 実装日: 2025-11-01

- [ ] **TASK-M04**: 例外メッセージ多言語方針（現在: 日/英 混在）整理
- [x] **TASK-M05**: CI ワークフロー強化（Python 3.11-3.14 マトリクス + Codecov連携）
  - [x] `.github/workflows/ci.yml` 大幅改善
  - [x] **テストマトリクスジョブ**（test-matrix）:
    - Python 3.11, 3.12, 3.13, 3.14 でのマトリクステスト
    - pre-commit フック統合（markdownlint, black, flake8, mypy）
    - カバレッジ収集（pytest-cov, 80%閾値）
    - Codecov連携（Python 3.12のみ、fail_ci_if_error: false）
    - HTMLカバレッジレポートのアーティファクトアップロード
  - [x] **Lintジョブ**（lint）:
    - black, isort, flake8, mypy, bandit の独立実行
    - Python 3.12のみで実行（lintは1バージョンで十分）
    - bandit: JSON + 標準出力レポート生成
  - [x] **オプショナル依存テスト**（optional-extras）:
    - 7つのextraグループ個別テスト（visualization, streaming, web, db, auth, io, logging）
    - スモークテスト（`-m "not slow" --maxfail=1 --no-cov`）
    - fail-fast: false（すべてのextraを確認）
  - [x] **完全インストールテスト**（full-install）:
    - `[full]` extra での全依存関係同時インストール
    - 完全なテストスイート実行（カバレッジ80%）
  - [x] `workflow_dispatch` トリガー追加（手動実行可能）
  - 実装日: 2025-11-01
  - 完了基準: ✅ Python 3.11-3.14でテスト可能、✅ Codecov連携、✅ 各extrasの動作確認

---

## 進捗ログ

| 日付       | 内容                                                                 |
| ---------- | -------------------------------------------------------------------- |
| 2025-10-03 | DataLoader リファクタ・例外統一・追加カバレッジテスト                |
| 2025-10-04 | レガシーコード削除 / 依存最小化 / キャッシュ統計追加 / tasks.md 更新 |

---

## Household Budget Analysis MCP Server - 実装計画（tasks.md）

- バージョン: v1.2
- 日付: 2025-10-30
- 作成者: GitHub Copilot
- ステージ: Stage 3（Implementation Planning）/ 承認済
- 参照: ./requirements.md（v1.0）, ./design.md（v0.4.0, 承認済）

## 変更履歴

- v1.2: 重複検出・解決機能の詳細タスク追加（FR-009拡張対応、T6-1〜T6-8追加）
- v1.1: 旧Python系/画像生成/HTTPストリーミングの計画を削除し、設計v1.0（Node.js/TS）へ整合
- v1.0: 初版（要件v1.0/設計v1.0に準拠）

## 0. 方針と範囲

- 対応FR: 001,002,003,004,005,006,007,008,009,011,014（010/012/013は将来）
- 対応TS: 001,002,003,004,005,006,007,009,010（008は対象外）
- 対応OS: Linux、入力: CSVのみ、通貨: JPY、プロファイル: 単一
- 技術: Node.js 20+ / TypeScript, SQLite(better-sqlite3), MCP SDK, pino, csv-parse

## 1. マイルストーン

- M1: プロジェクト基盤/DBスキーマ確立
- M2: CSV取り込み/正規化/重複除外（FR-001/002/009基本, TS-001/002/003）
- M2-A: 重複検出・解決機能（FR-009拡張, TS-003-1〜003-6）
- M3: 自動分類/ルール（FR-003, TS-004）
- M4: 集計/検索/予算/レポート（FR-004/005/006/007/008, TS-005/006/007）
- M5: MCPツール公開/日本語エラー（FR-011/014, TS-010/全般）
- M6: E2E/性能確認（TS-001〜007/009/010, NFR-002/011）

## 2. タスク一覧（チェックリスト）

- [ ] T1: リポジトリ初期化と基盤
  - 内容: Node.js/TS設定、lint/format、pino、dotenv、ディレクトリ構成（src/, data/, fixtures/）
  - 依存: なし / 見積: 0.5d
  - 完了基準: ビルド・実行・ロガー起動

- [ ] T2: SQLite層とマイグレーション
  - 内容: better-sqlite3接続、FTS5有効化、マイグレーション仕組み、スキーマ作成（design.md §4）
  - 依存: T1 / 見積: 1.0d
  - 完了基準: DB初期化コマンドでテーブル/インデックス作成

- [ ] T3: I18n/Errorサービス
  - 内容: 日本語メッセージ定義、標準化エラー形（{code,message,details}）、入力検証ヘルパ
  - 依存: T1 / 見積: 0.5d
  - 完了基準: 代表エラーで自然な日本語返却（TS-010）

- [ ] T4: CSVマッピングテンプレート（FR-001）
  - 内容: テンプレ保存/取得、date_format/encoding保持
  - 依存: T2,T3 / 見積: 0.5d
  - 完了基準: 保存/取得APIのユニットテスト

- [ ] T5: 取り込み/正規化/検証（FR-001/002）
  - 内容: csv-parseストリーム、マッピング適用、日付/金額正規化、行エラー収集
  - 依存: T2,T3,T4 / 見積: 1.5d
  - 完了基準: TS-001/002合格

- [ ] T6: 重複検出/除外（FR-009基本）
  - 内容: 正規化ハッシュ生成（design.mdの規約）、UNIQUE制約でskip、結果レポート
  - 依存: T5 / 見積: 0.5d
  - 完了基準: TS-003合格（同一ファイル再取込で件数不変）

- [ ] T6-1: SQLiteデータベース基盤構築（FR-009-3）
  - 内容:
    - `data/household.db` 初期化処理実装
    - `transactions` テーブル作成（重複管理フィールド含む）
    - `duplicate_checks` テーブル作成
    - パフォーマンス用インデックス作成
    - DatabaseManager クラス実装（初期化・セッション管理）
  - 依存: T2 / 見積: 1.0d
  - 完了基準: DBファイル生成、テーブルスキーマ確認、接続テスト成功

- [ ] T6-2: CSV→DBインポート機能（FR-009-3）
  - 内容:
    - CSVImporter クラス実装
    - CSV行→Transactionモデルへの変換
    - 重複チェック（source_file + row_number）
    - 一括インポート機能（全CSVファイル）
    - インポート結果レポート（imported/skipped/errors）
  - 依存: T5, T6-1 / 見積: 1.0d
  - 完了基準: サンプルCSVのDB取り込み成功、再実行でskipped件数が正しい

- [ ] T6-3: 重複検出エンジン（FR-009-1）
  - 内容:
    - DuplicateDetector クラス実装
    - DetectionOptions（日付誤差・金額誤差）の実装
    - 日付範囲でのグルーピング最適化
    - 基本条件チェック（_is_potential_duplicate）
    - 類似度スコア計算（_calculate_similarity）
    - 重複候補ペアの抽出とソート
  - 依存: T6-1 / 見積: 1.5d
  - 完了基準:
    - TS-003-1: 日付・金額完全一致で検出
    - TS-003-2: 日付±1日で検出
    - TS-003-3: 金額±10円または±1%で検出

- [ ] T6-4: ユーザー確認MCPツール（FR-009-2）
  - 内容:
    - `detect_duplicates` ツール実装（検出実行）
    - `list_duplicate_candidates` ツール実装（候補一覧取得）
    - `get_duplicate_candidate_detail` ツール実装（詳細表示）
    - `confirm_duplicate` ツール実装（判定記録）
    - `restore_duplicate` ツール実装（復元）
    - `get_duplicate_stats` ツール実装（統計）
    - 各ツールのJSON Schema定義
    - エラーハンドリング（日本語メッセージ）
  - 依存: T6-3, T3 / 見積: 1.5d
  - 完了基準: TS-003-4合格（ユーザー確認フロー動作）

- [ ] T6-5: 重複解消処理（FR-009-4）
  - 内容:
    - DuplicateResolver クラス実装
    - is_duplicate フラグ設定処理
    - duplicate_of 参照設定
    - トランザクション処理（原子性保証）
    - 誤判定時の復元機能
    - 処理履歴の記録（duplicate_checks更新）
  - 依存: T6-4 / 見積: 0.5d
  - 完了基準: TS-003-5/003-6合格（フラグ設定・復元動作）

- [ ] T6-6: 集計からの重複除外（FR-009-4）
  - 内容:
    - 既存集計クエリに `is_duplicate = 0` フィルタ追加
    - オプションで重複含む分析機能（監査用）
    - レポート出力時の重複除外
  - 依存: T6-5, T9 / 見積: 0.5d
  - 完了基準: 重複フラグが立った取引が集計から除外される

- [ ] T6-7: 重複検出の単体テスト（FR-009全般）
  - 内容:
    - `test_duplicate_detector.py` 実装
    - `test_csv_importer.py` 実装
    - `test_duplicate_tools.py` 実装
    - 各種誤差オプションのテストケース
    - エッジケース（同日同額・誤差境界値）
  - 依存: T6-3, T6-4, T6-5 / 見積: 1.0d
  - 完了基準: TS-003シリーズ全合格、カバレッジ80%以上

- [ ] T6-8: 重複検出の統合テスト（FR-009全般）
  - 内容:
    - `test_duplicate_pipeline.py` 実装
    - CSV取り込み→検出→確認→解消のE2Eフロー
    - 大量データ（1000件以上）での性能確認
    - 並行処理のテスト
  - 依存: T6-7 / 見積: 0.5d
  - 完了基準: E2Eシナリオ成功、NFR-011（データ永続性）確認

- [ ] T7: 分類ルールエンジン（FR-003）
  - 内容: priority/substring|regex|exact評価、最初一致採用、未分類はNULL
  - 依存: T2 / 見積: 1.0d
  - 完了基準: 代表ケースで正しくカテゴリが付与

- [ ] T8: 手動上書き/ルール追加（FR-003）
  - 内容: add_category_ruleツール、再分類で反映、簡易メトリクス（未分類率）
  - 依存: T7 / 見積: 0.5d
  - 完了基準: TS-004合格

- [ ] T9: 集計/検索（FR-004/005/008）
  - 内容: 粒度（日/週/月/年）集計、トップN、全文検索（FTS5）、タグ付与/除去/検索
  - 依存: T2,T5 / 見積: 1.5d
  - 完了基準: 代表クエリの数値一致、タグ検索動作

- [ ] T10: 予算（FR-006）
  - 内容: set_budget/get_budget_status、差異/達成率/警告計算
  - 依存: T2,T9 / 見積: 0.5d
  - 完了基準: TS-006合格

- [ ] T11: レポート出力（FR-007）
  - 内容: aggregate/transactionsのCSV/JSON出力、メタ付与、UTF-8
  - 依存: T9 / 見積: 0.5d
  - 完了基準: TS-007合格

- [ ] T12: MCPサーバ/ツール公開（FR-011/014）
  - 内容: @modelcontextprotocol/sdk設定、各ツール導線、JSON Schema検証、日本語エラー
  - 依存: T3,T4,T5,T6,T7,T8,T9,T10,T11 / 見積: 1.0d
  - 完了基準: 主要操作がMCP経由で実行可能（FR-011受入）

- [ ] T13: E2Eと性能（NFR-002, TS-001〜007/009/010）
  - 内容: fixtures準備、シナリオ自動化、10万件相当の性能確認
  - 依存: T12 / 見積: 1.0d
  - 完了基準: 全対象TS合格、主要クエリ<2秒

## 3. 依存関係（要約）

- T1 → T2 →（T4,T3）→ T5 → T6（基本重複検出）
- T2 → T6-1（DB基盤）→ T6-2（CSVインポート）, T6-3（重複検出エンジン）
- T5, T6-1 → T6-2
- T6-3, T3 → T6-4（MCPツール）→ T6-5（解消処理）
- T6-5, T9 → T6-6（集計除外）
- T6-3, T6-4, T6-5 → T6-7（単体テスト）→ T6-8（統合テスト）
- T2 → T7 → T8
- T2 → T9 →（T10, T11）
- すべての機能タスク（T6-6含む）→ T12 → T13

## 4. 工数見積（合計の目安）

- 基本機能: 約 10.0 人日
- 重複検出・解決拡張（T6-1〜T6-8）: 約 7.0 人日
- **合計: 約 17.0 人日**（小規模調整含む）

## 5. トレーサビリティ

- FR-001/002/009（基本） ↔ T4/T5/T6, TS-001/002/003
- FR-009-1（重複検出ロジック） ↔ T6-1/T6-2/T6-3, TS-003-1/003-2/003-3
- FR-009-2（ユーザー確認） ↔ T6-4, TS-003-4
- FR-009-3（DB永続化） ↔ T6-1/T6-2, NFR-011
- FR-009-4（重複解消） ↔ T6-5/T6-6, TS-003-5/003-6
- FR-003 ↔ T7/T8, TS-004
- FR-004/005/008 ↔ T9, TS-005
- FR-006 ↔ T10, TS-006
- FR-007 ↔ T11, TS-007
- FR-011/014 ↔ T12, TS-010
- NFR-002/011 ↔ T13

## 6. 実装順序の推奨フェーズ

### フェーズ A: 基盤構築（Week 1）

- T1: リポジトリ初期化
- T2: SQLite層
- T3: I18n/Error
- T6-1: DB基盤（transactions/duplicate_checks テーブル）

### フェーズ B: データ取り込み（Week 2）

- T4: CSVマッピングテンプレート
- T5: CSV取り込み/正規化
- T6: 基本重複検出
- T6-2: CSV→DBインポート

### フェーズ C: 重複検出・解決（Week 3）

- T6-3: 重複検出エンジン
- T6-4: ユーザー確認MCPツール
- T6-5: 重複解消処理
- T6-7: 単体テスト

### フェーズ D: 分類・集計（Week 4）

- T7: 分類ルールエンジン
- T8: 手動上書き
- T9: 集計/検索
- T6-6: 集計からの重複除外

### フェーズ E: 予算・レポート（Week 5）

- T10: 予算管理
- T11: レポート出力
- T12: MCPツール統合

### フェーズ F: テスト・検収（Week 6）

- T6-8: 重複検出統合テスト
- T13: E2E/性能テスト
- ドキュメント最終化

## 7. 完了条件（リリース基準）

- TS-001〜007/009/010 合格（基本機能）
- TS-003-1〜003-6 合格（重複検出・解決機能）
- NFR-002（パフォーマンス）、NFR-011（データ永続性）を満たす
- 重複検出MCPツール群が正常動作（6つのツール）
- 主要ツールの日本語エラー/I18n整備
- ローカルのみで一連の運用が完結（data/household.db含む）

---

- TS-001〜007/009/010 合格、NFR-002満たす
- 主要ツールの日本語エラー/I18n整備、ローカルのみで一連の運用が完結

---

## フェーズ6: 画像生成・HTTPストリーミング機能実装 (Week 6-7)

**対応設計**: design.md v0.3.0 第10章  
**対応要件**: FR-004〜FR-006（要件追加予定）、NFR-005〜NFR-007

### 実装済み状況

- [x] **基本可視化モジュール**: `src/household_mcp/visualization/chart_generator.py` 実装済み
  - ChartGenerator クラス、日本語フォント自動検出機能
  - 円グラフ、棒グラフ、折れ線グラフ、面グラフ生成機能
  - matplotlib 依存（optional: visualization extras）
- [x] **スタイル定義**: `src/household_mcp/visualization/styles.py` 実装済み
- [x] **例外クラス**: `ChartGenerationError` 定義済み（`src/household_mcp/exceptions.py`）

### 未実装タスク

- [x] **TASK-601**: 日本語フォント配置とロード検証（NFR-007）
  - [x] `fonts/` ディレクトリ作成
  - [x] Noto Sans CJK フォント配置（OFL ライセンス確認）
  - [x] ChartGenerator のフォント自動検出テスト
  - 見積: 0.5d
  - 完了基準: 日本語ラベル付きグラフが正常に生成される ✅
  - 実装日: 2025-11-01（検証完了）
  - 検証結果:
    - フォント自動検出: `/home/shun-h/my_household_mcpserver/fonts/NotoSansCJKjp-Regular.otf`
    - フォントサイズ: 16,467,736 bytes
    - 円グラフ生成: 55,942 bytes（日本語タイトル・ラベル正常）
    - 折れ線グラフ生成: 59,416 bytes（日本語カテゴリ名正常）
    - テスト: `test_chart_generator_japanese_font_rendering` PASSED

- [x] **TASK-602**: HTTPストリーミング基盤実装（FR-005, NFR-005）
  - [x] `src/household_mcp/streaming/image_streamer.py` 実装済み
    - BytesIO → チャンク配信機能（chunk_size: 8192 bytes）
    - 非同期ストリーミングヘルパー（async generator）
    - FastAPI StreamingResponse統合
  - [x] `src/household_mcp/streaming/cache.py` 実装済み
    - TTLCache ベースの画像キャッシュ（max_size: 50, ttl: 3600秒）
    - キャッシュキー生成（MD5ハッシュ、パラメータソート）
    - stats() メソッド（サイズ・ヒット率統計）
  - [x] `src/household_mcp/streaming/global_cache.py` 実装済み
    - グローバル共有キャッシュインスタンス管理
  - [x] 依存: pyproject.toml の `streaming` extras に cachetools>=5.3.0 設定済み
  - 見積: 1.0d
  - 完了基準: ✅ 画像データのメモリ内キャッシュとストリーミング配信が動作
  - 実装日: 既存実装（Phase 7期間中）

- [x] **TASK-603**: FastAPI HTTP サーバー実装（FR-005, NFR-005）
  - [x] `src/household_mcp/web/http_server.py` 実装済み（274行）
    - `/api/charts/{chart_id}` エンドポイント（画像ストリーミング）
    - `/api/charts/{chart_id}/info` エンドポイント（メタデータ取得）
    - `/api/cache/stats` エンドポイント（キャッシュ統計）
    - `DELETE /api/cache` エンドポイント（キャッシュクリア）
    - `/health` ヘルスチェックエンドポイント
    - StreamingResponse 実装（chunk_size: 8192 bytes）
    - CORS 設定（allow_origins=["*"], allow_methods=["GET"]）
  - [x] Webアプリ用APIエンドポイント追加
    - `/api/monthly` - 月次データ取得（JSON/画像対応）
    - `/api/available-months` - 利用可能な年月リスト
    - `/api/category-hierarchy` - カテゴリ階層情報
  - [x] create_http_app() ファクトリー関数（設定可能なCORS/キャッシュ）
  - [x] 依存: pyproject.toml の `web` extras 確認済み（FastAPI, uvicorn）
  - 見積: 1.0d
  - 完了基準: ✅ HTTP経由で画像取得が可能、同時接続5件対応（NFR-005）
  - 実装日: 既存実装（Phase 7期間中）

- [x] **TASK-604**: MCP ツール拡張（画像生成対応）（FR-004, FR-006）
  - [x] `src/household_mcp/tools/enhanced_tools.py` 実装済み（290行）
    - `output_format` パラメータ実装（"text" | "image"）
    - `graph_type` パラメータ実装（"pie" | "bar" | "line" | "area"）
    - `image_size`, `image_format` パラメータ実装
  - [x] 既存ツールのラッパー実装済み
    - `enhanced_monthly_summary()` - 月次サマリー（テキスト/画像）
    - `enhanced_category_trend()` - カテゴリ別トレンド（テキスト/画像）
  - [x] 画像生成時のURL返却ロジック実装
    - ChartGenerator → グローバルキャッシュ → HTTP URL
    - キャッシュキー生成（kind, year, month, graph_type, image_size, image_format）
  - [x] オプショナル依存チェック（visualization, streaming extras）
  - [x] エラーハンドリング（DataSourceError, 依存関係不足）
  - 見積: 1.0d
  - 完了基準: ✅ MCPクライアントから画像形式でのレスポンス取得が可能
  - 実装日: 既存実装（Phase 7期間中）

- [x] **TASK-605**: category_analysis ツール実装完了（FR-002, FR-003）
  - [x] `server.py` の `category_analysis` スタブを実装
    - 期間指定でのカテゴリ別集計
    - 前月比・前年比計算（CategoryTrendAnalyzer使用）
    - トップN支出の抽出（max_month/min_month実装）
  - [x] 入出力バリデーション
  - [x] 日本語エラーメッセージ（全エラーパスで対応済み）
  - 見積: 0.5d
  - 完了基準: category_analysis が実データで動作、エラーが日本語で返る ✅
  - 完了日: 2025-11-01（実装確認済み）

- [x] **TASK-606**: 統合テスト（画像生成〜配信）（TS-008, NFR-005〜007）
  - [x] `tests/integration/test_streaming_pipeline.py` 実装済み（292行、11テスト）
  - [x] **E2Eテスト**:
    - test_end_to_end_monthly_summary_image: 月次サマリー画像生成E2E ✅
    - test_end_to_end_category_trend_image: カテゴリトレンド画像生成E2E ✅
  - [x] **パフォーマンステスト（NFR-005/006）**:
    - test_performance_image_generation_within_3_seconds: 画像生成3秒以内 ✅
    - test_cache_hit_performance: キャッシュヒット0.5秒以内 ✅
    - test_memory_usage_within_50mb: メモリ使用量50MB以内 ✅
  - [x] **並行処理テスト**:
    - test_concurrent_image_generation: 複数画像の並行生成 ✅
  - [x] **キャッシュテスト**:
    - test_cache_stats_tracking: キャッシュ統計追跡 ✅
  - [x] **エラーハンドリングテスト**:
    - test_error_handling_invalid_data: 不正データのエラー処理 ✅
    - test_error_handling_missing_visualization_deps: 依存関係不足エラー ✅
  - [x] **画像フォーマット検証**:
    - test_image_format_validation: PNG形式の検証 ✅
  - [x] **インポートテスト**:
    - test_streaming_imports: ストリーミングモジュールインポート ✅
  - 見積: 1.5d
  - 完了基準: ✅ 全テスト合格（11/11 PASSED）、NFR-005〜007 基準達成
  - テスト実行日: 2025-11-01
  - パフォーマンス結果:
    - 画像生成時間: < 3秒（NFR-005準拠）
    - キャッシュヒット: < 0.5秒
    - メモリ増加: < 50MB（NFR-006準拠）
    - PNG形式検証: マジックナンバー確認済み

- [ ] **TASK-607**: パフォーマンス最適化とNFR検証（NFR-005, NFR-006）
  - [ ] matplotlib 描画設定最適化
  - [ ] メモリプロファイリング（memory_profiler）
  - [ ] 転送速度ベンチマーク
  - [ ] 同時接続テスト(5件同時)
  - 見積: 1.0d
  - 完了基準:
    - 画像生成 < 3秒
    - メモリ使用 < 50MB
    - 転送速度 > 1MB/秒
    - 同時接続5件で安定動作

### 依存関係管理

- [x] **TASK-608**: 依存関係の整理と更新
  - [x] `pyproject.toml` の `visualization` extras 確認済み
    - matplotlib>=3.8.0 ✅
    - plotly>=5.17.0 ✅
    - pillow>=10.0.0 ✅
  - [x] `streaming` extras 確認済み
    - fastapi>=0.100.0 ✅
    - uvicorn[standard]>=0.23.0 ✅
    - cachetools>=5.3.0 ✅
  - [x] `web` extras の FastAPI/uvicorn バージョン確認済み
    - fastapi>=0.100.0 ✅
    - pydantic>=2.11,<3 ✅
    - python-multipart>=0.0.6 ✅
  - [x] README.md にインストール手順完備
    - 各extrasの詳細説明セクション追加済み
    - 依存関係最小化ポリシーの文書化済み（TASK-M01）
    - full extras インストール手順記載済み
  - 見積: 0.5d
  - 完了基準: ✅ `uv pip install -e ".[full]"` で全機能が利用可能
  - 検証日: 2025-11-01

### ドキュメント更新

- [x] **TASK-609**: 設計書・要件定義の整合性修正
  - [x] `design.md` ヘッダーに requirements.md v1.2 への参照を明記
  - [x] `design.md` に実装状況セクションを追加
    - FR-001〜FR-003, FR-018（Webアプリ）: 実装済み
    - FR-004〜FR-006（画像生成・ストリーミング）: 部分実装（基盤のみ）
    - FR-007〜FR-017: 計画中（Node.js/TS版）
  - [x] `requirements.md` は既に v1.2 で最新（画像生成・Webアプリ含む）
  - 見積: 0.5d
  - 完了基準: 設計書と要件定義の version/対象要件が一致 ✅
  - 完了日: 2025-11-01
  - 注記: requirements.md は既に FR-001〜FR-018 を含む v1.2 で最新状態でした

- [x] **TASK-610**: ユーザー向けドキュメント更新
  - [x] `README.md` に画像生成機能の詳細セクション追加
    - インストール方法（visualization + streaming extras）
    - 日本語フォント設定ガイド（自動検出の説明）
    - 起動方法（ストリーミングモード/stdioモード）
    - MCPツール使用例（enhanced_monthly_summary, enhanced_category_trend）
    - サポートされるグラフタイプ（pie, bar, line, area）
  - [x] HTTP APIエンドポイント完全ドキュメント化
    - GET /api/charts/{chart_id} - 画像ストリーミング配信
    - GET /api/charts/{chart_id}/info - メタデータ取得
    - GET /api/cache/stats - キャッシュ統計
    - DELETE /api/cache - キャッシュクリア
    - GET /health - ヘルスチェック
    - 各エンドポイントのリクエスト/レスポンス例を記載
  - [x] `docs/usage.md` 画像生成サンプル確認済み
    - テキスト/画像形式リクエスト例
    - レスポンス形式の詳細
    - curlコマンドでの画像取得例
  - [x] `docs/api.md` 新規エンドポイント確認済み
    - enhanced_monthly_summary, enhanced_category_trend の詳細仕様
    - パラメータ、レスポンス形式、エラーコード
    - キャッシング戦略とパフォーマンス特性
  - 見積: 0.5d
  - 完了基準: ✅ ユーザーが画像生成機能を理解・利用できるドキュメント完備
  - 実装日: 2025-11-01

---

## フェーズ6 マイルストーン

| マイルストーン | 目標週 | 完了条件                                                                 | 状態   |
| -------------- | ------ | ------------------------------------------------------------------------ | ------ |
| MS-6.1         | Week 6 | フォント配置・ストリーミング基盤・HTTP サーバー実装完了（TASK-601〜603） | ✅完了 |
| MS-6.2         | Week 6 | MCP ツール拡張・category_analysis 実装完了（TASK-604〜605）              | ✅完了 |
| MS-6.3         | Week 7 | テスト・NFR 検証・依存関係整理完了（TASK-606〜608）                      | 🔄進行 |
| MS-6.4         | Week 7 | ドキュメント更新完了、画像生成機能リリース準備完了（TASK-609〜610）      | 🔄進行 |

---

## 全体進捗サマリ（2025-11-01 更新）

### 完了済みフェーズ

- [x] **フェーズ0**: 既存基盤の棚卸し
- [x] **フェーズ1**: インフラ・ユーティリティ整備（Week 1）
- [x] **フェーズ2**: トレンド分析コア実装（Week 2）
- [x] **フェーズ3**: MCP リソース・ツール追加（Week 3）
- [x] **フェーズ4**: テスト & 品質ゲート（Week 4）- 完了
  - ✅ TASK-401/402: 単体・統合テスト（8+8=16テスト追加）
  - ✅ TASK-M01~M05: メンテナンスタスク完了
    - M01: 依存関係最小化ポリシー文書化
    - M02: ロギング設定ヘルパー実装
    - M03: キャッシュ統計インターフェース追加
    - M04: 例外メッセージ多言語方針整理（スキップ）
    - M05: CI/CDワークフロー強化（Python 3.11-3.14マトリクス + Codecov）
- [x] **フェーズ5**: ドキュメント & 運用準備（Week 5）- 完了
  - ✅ TASK-501: ドキュメント更新（README.md全面改訂、Phase 6/7機能反映）
  - ✅ TASK-502: サンプル会話・FAQ整備（examples.md 14例、FAQ.md 48項目）
  - ✅ TASK-503: 検収手順確立

### 新規追加フェーズ

- [x] **フェーズ6**: 画像生成・HTTPストリーミング機能実装（Week 6-7）
  - ✅ TASK-601: 日本語フォント配置（完了）
  - ✅ TASK-602: HTTPストリーミング基盤（実装済み）
  - ✅ TASK-603: FastAPI HTTPサーバー（実装済み）
  - ✅ TASK-604: MCPツール拡張（実装済み）
  - ✅ TASK-605: category_analysis実装（完了）
  - 🔄 TASK-606: 統合テスト（未着手）
  - 🔄 TASK-607: パフォーマンス最適化（未着手）
  - 🔄 TASK-608: 依存関係整理（未着手）
  - ✅ TASK-609: 設計書整合性修正（完了）
  - 🔄 TASK-610: ユーザードキュメント更新（未着手）
- [x] **フェーズ7**: Webアプリケーション実装（Week 8）- 完了（TASK-701~705完了）

---

## フェーズ7: Webアプリケーション実装 (Week 8) - 完了

### TASK-701: バックエンドAPI拡張（FR-018-1）

- [x] **TASK-701-1**: http_server.pyにREST APIエンドポイント追加
  - [x] `GET /api/monthly` - 月次データ取得（JSON形式）
  - [x] `GET /api/available-months` - 利用可能な年月リスト
  - [x] `GET /api/category-hierarchy` - カテゴリ階層情報
  - [x] エラーハンドリング（HTTPException）
  - [x] パラメータバリデーション（FastAPI Query）

- [x] **TASK-701-2**: CORS設定の確認
  - [x] `allow_origins=["*"]` 設定確認
  - [x] `allow_methods=["GET"]` 設定
  - [x] 開発環境でのクロスオリジンアクセステスト

### TASK-702: Webアプリケーションの実装（FR-018-2）

- [x] **TASK-702-1**: プロジェクト構造の作成
  - [x] `webapp/` ディレクトリ作成
  - [x] `webapp/css/`, `webapp/js/` サブディレクトリ作成
  - [x] サーバーコードと完全分離

- [x] **TASK-702-2**: HTML/CSS実装
  - [x] `index.html` - メインUIレイアウト
  - [x] `css/style.css` - レスポンシブデザイン実装
  - [x] CSS Variables によるテーマ管理
  - [x] モバイル/タブレット/PC対応

- [x] **TASK-702-3**: JavaScript実装
  - [x] `js/api.js` - API通信クライアント（APIClient クラス）
  - [x] `js/chart.js` - Chart.js統合（ChartManager クラス）
  - [x] `js/main.js` - アプリケーションロジック
  - [x] 非同期データ読み込み
  - [x] エラーハンドリング
  - [x] ローディングインジケーター

### TASK-703: UI機能実装

- [x] **TASK-703-1**: コントロールパネル
  - [x] 年月選択ドロップダウン（動的生成）
  - [x] グラフタイプ選択（円/棒/折れ線）
  - [x] データ読み込みボタン
  - [x] エラーメッセージ表示エリア

- [x] **TASK-703-2**: 統計サマリー
  - [x] 総支出カード
  - [x] 取引件数カード
  - [x] 平均支出カード
  - [x] 最大支出カード
  - [x] 通貨フォーマット（¥区切り）

- [x] **TASK-703-3**: グラフ表示
  - [x] Chart.js CDN統合
  - [x] 円グラフ実装（カテゴリ別集計）
  - [x] 棒グラフ実装（カテゴリ別比較）
  - [x] 折れ線グラフ実装（日別推移）
  - [x] グラフタイプ切り替え
  - [x] カラーパレット自動生成

- [x] **TASK-703-4**: データテーブル
  - [x] 取引明細の表形式表示
  - [x] 検索機能（日付・内容）
  - [x] カテゴリフィルタ
  - [x] XSS対策（escapeHtml）

### TASK-704: テスト・検証

- [x] **TASK-704-1**: 動作確認
  - [x] バックエンドサーバー起動確認（ポート8000）
  - [x] Webアプリサーバー起動確認（ポート8080）
  - [x] API通信テスト（curl）
  - [x] データ読み込みテスト（2025年1月）
  - [x] グラフ描画確認

- [x] **TASK-704-2**: ブラウザテスト
  - [x] レスポンシブデザイン確認
  - [x] エラーハンドリング確認
  - [x] ローディング表示確認

### TASK-705: ドキュメント整備

- [x] **TASK-705-1**: Webアプリドキュメント作成
  - [x] `webapp/README.md` - 使い方・起動方法
  - [x] API仕様記載
  - [x] トラブルシューティング

- [x] **TASK-705-2**: メインREADME更新
  - [x] Webアプリセクション追加
  - [x] 起動方法の記載
  - [x] スクリーンショット準備（将来）

- [x] **TASK-705-3**: 設計書更新
  - [x] requirements.md - FR-018 追加
  - [x] design.md - セクション11追加（Webアプリ設計）
  - [x] tasks.md - フェーズ7追加（このセクション）

---

## フェーズ7 完了サマリー

### 実装された成果物

1. **バックエンドAPI**: 3つの新規エンドポイント
2. **Webアプリ**: 完全な独立フロントエンド（5ファイル）
3. **ドキュメント**: 3つのマークダウンファイル更新

### 技術的詳細

- **フロントエンド**: Vanilla JavaScript + Chart.js
- **バックエンド**: FastAPI + HouseholdDataLoader統合
- **コード分離**: サーバーとWebアプリの完全分離
- **依存関係**: 外部フレームワーク不要（Chart.js CDNのみ）

### 工数実績

- TASK-701: 1.0日（API実装）
- TASK-702: 2.0日（HTML/CSS/JS実装）
- TASK-703: 2.0日（UI機能実装）
- TASK-704: 0.5日（テスト）
- TASK-705: 0.5日（ドキュメント）
- **合計**: 6.0日

---

### 主要な技術的負債

1. **単体・統合テストの不足**（TASK-401, TASK-402）
2. **ドキュメント未更新**（TASK-501, TASK-502）
3. **設計書バージョン不整合**（0.2.0 → 0.3.0）
4. **画像生成機能の統合未完了**（TASK-602〜604）
5. **日本語フォント未配置**（TASK-601）

---

## 次アクション（優先順位順）

### 高優先度（即座に着手可能）

1. **TASK-601**: 日本語フォント配置（0.5d）
2. **TASK-401/402**: 単体・統合テスト追加（品質保証）
3. **TASK-501/502**: ドキュメント・FAQ整備

### 中優先度（依存関係あり）

1. **TASK-602**: HTTPストリーミング基盤（1.0d）
2. **TASK-603**: FastAPI HTTPサーバー（1.0d）
3. **TASK-604**: MCPツール拡張（1.0d）
4. **TASK-608**: 依存関係整理（0.5d）

### 低優先度（機能完成後）

1. **TASK-606**: 統合テスト（1.5d）
2. **TASK-607**: パフォーマンス最適化（1.0d）
3. **TASK-610**: ユーザードキュメント更新（0.5d）

### フェーズ4/5 残タスク

1. **TASK-401**: 単体テスト追加
2. **TASK-402**: 統合テスト整備
3. **TASK-501**: README更新
4. **TASK-502**: サンプル会話・FAQ整備

---

## 工数見積（フェーズ6追加分）

- フェーズ6: 約 7.5 人日
- 全体（フェーズ0〜6）: 約 17.5 人日

---
