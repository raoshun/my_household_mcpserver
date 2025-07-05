# 学習支援システム

VS Code統合型の学習効率化・TDD実践・バージョン管理支援システムです。

## 概要

このシステムは、家計簿MCPサーバプロジェクトにおける学習効率化と品質向上を目的として開発されました。以下の機能を提供します：

- 理解度確認と段階的学習支援
- TDD実践の追跡と指導
- 復習スケジュール管理
- バージョン管理の自動化
- 統合的な学習状況チェック

## システム構成

```
.learning_support/
├── understanding_checker.py    # 理解度確認ツール
├── learning_path_generator.py  # 学習パス生成ツール
├── tdd_tracker.py             # TDD実践追跡ツール
├── review_scheduler.py        # 復習スケジューラー
├── changelog_helper.py        # Changelogヘルパー
├── full_learning_check.py     # 統合学習チェック
└── learning_data.json         # 学習データ（自動生成）
```

## インストールと設定

### 1. 依存関係のインストール

```bash
pip install pandas chardet towncrier
```

### 2. VS Code設定

以下のファイルが自動的に設定されています：

- `.vscode/settings.json`: ワークスペース設定
- `.vscode/tasks.json`: タスク定義
- `.vscode/launch.json`: デバッグ設定
- `.vscode/extensions.json`: 推奨拡張機能

### 3. 実行権限の設定

```bash
chmod +x .learning_support/*.py
```

## 使用方法

### VS Codeタスクを使用する場合

1. `Ctrl+Shift+P` でコマンドパレットを開く
2. `Tasks: Run Task` を選択
3. 以下のタスクから選択：
   - `Learning Support: Check Understanding`
   - `Learning Support: Generate Learning Path`
   - `Learning Support: Record TDD Practice`
   - `Learning Support: Check Review Schedule`
   - `Learning Support: Full Check`
   - `Towncrier: Create Feature Fragment`
   - `Towncrier: Create Bugfix Fragment`

### コマンドラインを使用する場合

#### 理解度確認
```bash
python .learning_support/understanding_checker.py "CSVリーダー"
```

#### 学習パス生成
```bash
python .learning_support/learning_path_generator.py "SQLiteの複雑なJOINクエリ" kinesthetic
```

#### TDD実践記録
```bash
# REDフェーズ
python .learning_support/tdd_tracker.py red "CSVリーダー" "tests/test_csv_reader.py"

# GREENフェーズ
python .learning_support/tdd_tracker.py green "CSVリーダー" "tests/test_csv_reader.py" "src/csv_reader.py"

# REFACTORフェーズ
python .learning_support/tdd_tracker.py refactor "CSVリーダー" "tests/test_csv_reader.py" "src/csv_reader.py"
```

#### 復習スケジュール確認
```bash
# スケジュール確認
python .learning_support/review_scheduler.py --check

# 復習実施
python .learning_support/review_scheduler.py --review "CSVリーダー"
```

#### 変更フラグメント作成
```bash
# 機能追加
python .learning_support/changelog_helper.py create feature "新機能を追加"

# バグ修正
python .learning_support/changelog_helper.py create bugfix "バグを修正"
```

#### 統合チェック
```bash
# 全体チェック
python .learning_support/full_learning_check.py

# 特定概念のチェック
python .learning_support/full_learning_check.py "CSVリーダー"
```

## 主要機能

### 1. 理解度確認システム

**目的**: 実装前に作業者の理解度を確認し、適切な学習戦略を決定

**機能**:
- 5段階の理解度評価（not_assessed, beginner, intermediate, advanced, expert）
- 前提知識チェーンの確認
- TDD実践度の評価
- 省略判定（条件を満たす場合は確認を省略）

**使用例**:
```bash
python .learning_support/understanding_checker.py "pandasライブラリ"
```

### 2. 学習パス生成システム

**目的**: 個別化された効率的な学習パスを自動生成

**機能**:
- 知識依存関係グラフに基づく学習順序の最適化
- 学習スタイル別の個別化対応
- 推定学習時間の算出
- 練習問題と検証基準の自動生成

**学習スタイル**:
- `visual`: 図表・フローチャート重視
- `auditory`: 口頭説明・ディスカッション重視
- `kinesthetic`: 実際のコーディング重視
- `logical`: 体系的・理論的学習重視
- `balanced`: バランス型

**使用例**:
```bash
python .learning_support/learning_path_generator.py "MCPサーバ" visual
```

### 3. TDD実践追跡システム

**目的**: TDDサイクルの実践を追跡し、実践度を向上

**機能**:
- Red-Green-Refactorサイクルの記録
- フェーズ別成功率の追跡
- TDD実践度の自動評価
- フェーズ別ガイダンスの提供

**TDDフェーズ**:
- `red`: 失敗テストの作成
- `green`: 最小実装
- `refactor`: コード品質向上

**使用例**:
```bash
python .learning_support/tdd_tracker.py red "データベース操作" "tests/test_database.py"
```

### 4. 復習スケジュール管理システム

**目的**: 忘却曲線に基づく効率的な復習スケジュールを管理

**機能**:
- 間隔反復学習スケジュールの自動設定
- 個別化された復習間隔の計算
- 期限到来復習項目の自動検出
- 優先度に基づく復習順序の提案

**復習間隔**:
- 初回: 即座
- 2回目: 1日後
- 3回目: 3日後
- 4回目: 1週間後
- 5回目: 2週間後
- 6回目: 1ヶ月後
- 7回目以降: 3ヶ月後

**使用例**:
```bash
python .learning_support/review_scheduler.py --check
```

### 5. バージョン管理支援システム

**目的**: towncrierを使用した構造化されたChangelog管理

**機能**:
- 変更フラグメントの自動作成
- セマンティックバージョニングの提案
- 変更タイプ別の分類
- Changelog生成の自動化

**変更タイプ**:
- `feature`: 新機能
- `bugfix`: バグ修正
- `doc`: ドキュメント
- `removal`: 削除・非推奨
- `misc`: その他

**使用例**:
```bash
python .learning_support/changelog_helper.py create feature "新しいMCPツールを追加"
```

### 6. 統合学習チェックシステム

**目的**: 学習状況の総合的な確認と推奨事項の提示

**機能**:
- 全概念の学習状況サマリー
- 理解度・TDD実践度の分布表示
- 要注意概念の特定
- 総合的な推奨事項の生成

**使用例**:
```bash
python .learning_support/full_learning_check.py
```

## データ構造

### 学習データ (`learning_data.json`)

```json
{
  "concepts": {
    "概念名": {
      "understanding_level": "intermediate",
      "tdd_proficiency": "advanced", 
      "last_confirmed": "2025-07-06T10:30:00",
      "implementation_count": 5,
      "error_count": 1,
      "learning_path_completed": true,
      "prerequisites": ["前提知識1", "前提知識2"],
      "related_concepts": ["関連概念1"],
      "notes": "メモ"
    }
  },
  "learning_paths": {
    "概念名": {
      "target_concept": "目標概念",
      "identified_gap": "特定されたギャップ",
      "starting_point": "開始点",
      "steps": [...],
      "total_estimated_time": 180,
      "learning_style": "kinesthetic",
      "created_at": "2025-07-06T10:30:00"
    }
  },
  "tdd_records": [
    {
      "concept": "概念名",
      "phase": "red",
      "timestamp": "2025-07-06T10:30:00",
      "test_file": "tests/test_example.py",
      "implementation_file": "src/example.py",
      "success": true,
      "error_message": null,
      "notes": ""
    }
  ],
  "review_schedule": {
    "概念名": {
      "review_count": 2,
      "next_review_date": "2025-07-13T10:30:00",
      "last_review_date": "2025-07-06T10:30:00",
      "understanding_level": "intermediate",
      "tdd_proficiency": "advanced",
      "priority": 3,
      "notes": ""
    }
  }
}
```

## ワークフロー例

### 新機能実装時の推奨ワークフロー

1. **理解度確認**
   ```bash
   python .learning_support/understanding_checker.py "新機能名"
   ```

2. **学習パス生成（必要に応じて）**
   ```bash
   python .learning_support/learning_path_generator.py "新機能名" kinesthetic
   ```

3. **TDD実践**
   ```bash
   # REDフェーズ
   python .learning_support/tdd_tracker.py red "新機能名" "tests/test_new_feature.py"
   
   # GREENフェーズ
   python .learning_support/tdd_tracker.py green "新機能名" "tests/test_new_feature.py" "src/new_feature.py"
   
   # REFACTORフェーズ
   python .learning_support/tdd_tracker.py refactor "新機能名" "tests/test_new_feature.py" "src/new_feature.py"
   ```

4. **変更記録**
   ```bash
   python .learning_support/changelog_helper.py create feature "新機能の説明"
   ```

5. **復習スケジュール設定**
   ```bash
   python .learning_support/review_scheduler.py --schedule "新機能名"
   ```

### 定期メンテナンス時の推奨ワークフロー

1. **統合チェック**
   ```bash
   python .learning_support/full_learning_check.py
   ```

2. **復習実施**
   ```bash
   python .learning_support/review_scheduler.py --check
   python .learning_support/review_scheduler.py --review "復習対象概念"
   ```

3. **Changelog生成**
   ```bash
   towncrier --draft  # プレビュー
   towncrier --version 1.0.0  # 本番生成
   ```

## カスタマイズ

### 学習間隔の調整

`review_scheduler.py`の`review_intervals`を編集：

```python
self.review_intervals = {
    0: 0,      # 即座
    1: 1,      # 1日後
    2: 3,      # 3日後
    3: 7,      # 1週間後
    4: 14,     # 2週間後
    5: 30,     # 1ヶ月後
    6: 90      # 3ヶ月後
}
```

### 知識依存関係の追加

`learning_path_generator.py`の`_build_knowledge_graph()`を編集：

```python
"新概念": {
    "prerequisites": ["前提知識1", "前提知識2"],
    "difficulty": "intermediate",
    "estimated_time": 120,
    "learning_methods": {
        "visual": "学習方法",
        "auditory": "学習方法", 
        "kinesthetic": "学習方法",
        "logical": "学習方法"
    }
}
```

## トラブルシューティング

### よくある問題

1. **学習データが読み込めない**
   ```bash
   # データファイルの権限を確認
   ls -la .learning_support/learning_data.json
   
   # 必要に応じて権限を修正
   chmod 644 .learning_support/learning_data.json
   ```

2. **Pythonパスが見つからない**
   ```bash
   # Pythonパスを確認
   which python
   which python3
   
   # 必要に応じてシンボリックリンクを作成
   ln -s /usr/bin/python3 /usr/local/bin/python
   ```

3. **VS Codeタスクが実行できない**
   ```bash
   # ワークスペースを再読み込み
   # Ctrl+Shift+P -> "Developer: Reload Window"
   ```

### ログとデバッグ

学習支援システムは詳細なログを出力します。問題が発生した場合は、以下を確認してください：

1. コンソール出力のエラーメッセージ
2. `.learning_support/learning_data.json`の内容
3. VS Codeの問題パネル
4. ターミナルでの直接実行結果

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 貢献

バグ報告や機能要求は、GitHubのIssuesでお願いします。プルリクエストも歓迎します。
