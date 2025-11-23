# 家計簿分析 MCP サーバー タスク計画

- **バージョン**: 1.1.0 (Refactoring Phase)
- **更新日**: 2025-11-21
- **アーカイブ**: [tasks_archive_20251121.md](docs/archive/tasks_archive_20251121.md)

## リファクタリングフェーズ (Current)

### ドキュメント整理

- [x] **TASK-REF-001**: `tasks.md` のアーカイブとスリム化
- [x] **TASK-REF-002**: `design.md` の整理（Phase 15以前の記述をアーカイブまたは要約）

### コード整理

- [x] **TASK-REF-003**: `trend_tool.py` と `trend_tool_db.py` の統合
  - `CategoryTrendAnalyzer` のデータソース抽象化
  - `trend_tool_db.py` の削除
- [x] **TASK-REF-004**: `analytics_tools.py` の `analysis_tools.py` への統合検討と実施
- [x] **TASK-REF-005**: 不要なファイルの削除 (`backend/src/household_mcp/server/` など)
- [x] **TASK-REF-006**: `financial_independence_tools.py` のリファクタリング
  - コード行数の削減と複雑度の低減
  - テストの安定化（モックの導入）
  - エラーハンドリングの改善

---

## フェーズ18: 収入分析・強化FIRE計算 (Nov 16-30, 2025)

### 📋 フェーズ概要

**目的**: 家計簿CSVデータから収入を分析し、支出との対比でキャッシュフローを管理する機能を実装。FIRE計算の精度向上と、実際の資産形成ペースの可視化を実現する。

**対象要件**: FR-032（収入分析）、FR-033（強化FIRE）、FR-034（MCPツール）  
**実装期間**: 11-14日（2-3週間）  
**優先度**: HIGH（Phase 1, 2）、MEDIUM（Phase 3）

---

### Phase 1: 基礎分析機能（3-4日）

- [x] **TASK-2001**: IncomeAnalyzer 基礎実装（1.0d）
- [x] **TASK-2002**: SavingsRateCalculator 実装（1.0d）
- [x] **TASK-2003**: RealEstateCashflowAnalyzer 実装（1.0d）
- [x] **TASK-2004**: Phase 1 単体テスト（1.0d）

### Phase 2: FIRE計算強化（4-5日）

- [x] **TASK-2005**: EnhancedFIRESimulator 基礎実装（1.5d）
- [x] **TASK-2006**: 4種類のFIREタイプサポート（1.0d）
- [x] **TASK-2007**: シナリオ比較機能（1.0d）
- [x] **TASK-2008**: Phase 2 単体テスト（1.0d）

### Phase 3: 高度機能・統合（4-5日）

- [x] **TASK-2009**: What-Ifシミュレーション（1.0d）
- [x] **TASK-2010**: MCPツール実装（1.0d）
- [x] **TASK-2011**: REST API実装（0.75d）
  - 完了日: 2025-11-17
  - 実績: `/api/financial-independence/scenarios`, `/api/financial-independence/what-if` 実装完了
  - annual_expense を必須とする修正（FIREScenario, tools, routes）を含む
- [x] **TASK-2012**: 統合テスト（1.0d）
  - 完了日: 2025-11-17
  - 実績: `tests/integration/test_fire_scenarios_api.py` の 6 テスト全て PASSED
    - うち what-if テストでは annual_expense と変更サマリ構造を検証
  - ⚠️ 注意: プロジェクト全体のカバレッジは 18%（閾値 80% 未達）。次タスク TASK-2017 で計画。
- [x] **TASK-2013**: ドキュメント整備（0.75d）
  - FR-035/036 を requirements.md, design.md に追記完了（2025-11-17）
  - 残作業: README/examples/docs での analysis_tools 参照更新、What-If 例文追加

### Phase 4: データベース・インフラ（並行作業）

- [x] **TASK-2014**: income_snapshots テーブル作成（0.5d）
  - 完了日: 2025-11-17
  - 実績:
    - `backend/src/household_mcp/database/models.py`: IncomeSnapshot ORM モデル追加
    - テーブル構造: snapshot_month (YYYY-MM, UNIQUE), 5つの収入カテゴリ列、total_income, savings_rate, timestamps
    - Index: idx_income_snapshot_month (UNIQUE on snapshot_month)
    - `backend/scripts/migrate_fi_tables.py`: income_snapshots 作成/削除/検証関数追加
    - マイグレーション実行: ✅ 4テーブル全て検証完了 (expense_classification, fi_progress_cache, fire_asset_snapshots, income_snapshots)
  - コミット: 97fd2fb

- [x] **TASK-2015**: キャッシング実装（0.5d）
  - 完了日: 2025-11-17
  - 実績:
    - `backend/src/household_mcp/analysis/income_analyzer.py` にキャッシング機能追加
    - CACHE_TTL_SECONDS = 3600 (1時間、NFR-040 準拠)
    - `get_monthly_summary()`: キャッシュファースト戦略 (cache check → load OR calculate → save)
    - `_get_cached_snapshot()`: DB から snapshot 取得、TTL 検証（1時間以内）
    - `_save_snapshot_to_cache()`: upsert パターン（UPDATE 先行、失敗時 INSERT）
    - `_load_summary_from_snapshot()`: DB から IncomeSummary 復元
    - db_manager 引数追加（optional、デフォルト None でグレースフルデグラデーション）
    - テスト: `test_income_caching.py` (5/5 PASSED) - cache miss/hit/expiration/update/without-db
    - カバレッジ: income_analyzer.py 27% → 78% (+51% ✅)
  - コミット: 97fd2fb

### Phase 5: メンテナンス・クリーンアップ（新規）

- [x] **TASK-2016**: 命名統一リファクタ（FR-035）（0.5d）
  - 完了日: 2025-11-17
  - phase16_tools.py 削除完了（互換性不要と判断）
  - 全参照は analysis_tools に統一済み（ルータ/ツール/ドキュメント）
  - lintエラー整理（long lines等）対応済み
- [x] **TASK-2017**: カバレッジ回復計画A（FR-029）（0.5d）
  - 完了日: 2025-11-17
  - 選択肢A（スモークテスト追加）を実施
  - `test_enhanced_fire_simulator_smoke.py` 追加（6テスト: 4種類のFIREタイプ + what-if 2種）
  - 成果:
    - カバレッジ 18.11% → 18.62% (+0.51%、確実な改善確認 ✅)
    - `enhanced_fire_simulator.py` 70% → 87% (+17% ✅)
    - 統合テスト (6) + スモークテスト (6) = 12テスト全PASSED
  - 次ステップ: 80%閾値到達にはさらなる取り組みが必要（Phase 4でDB/キャッシュ実装後に再評価）

**合計**: 17タスク、約13日

## Phase 17: 家計改善機能の実装

**目的**: 分析ツールを実データ連携させ、能動的な家計改善支援を実現する。

- [x] **TASK-1701**: `analyze_expense_patterns` の実データ化 (FR-021)
  - `HouseholdDataLoader` を使用してCSVデータを取得
  - `ExpensePatternAnalyzer` を使用して分類を実行
  - ダミーデータを廃止
- [x] **TASK-1702**: `suggest_improvement_actions` の実データ化 (FR-022)
  - 実支出データに基づく削減提案ロジックの実装
  - 変動費・固定費の分類結果を活用
- [x] **TASK-1703**: `detect_spending_anomalies` の実装 (FR-023)
  - 新規MCPツールとして実装
  - 過去平均との乖離（σ）を計算し、異常値を検出
- [x] **TASK-1704**: `project_financial_independence_date` の実データ化 (FR-024)
  - `FireSnapshotService` から現在資産を取得
  - 実支出データから年間支出を算出
  - FIRE達成予測をリアルタイム計算
