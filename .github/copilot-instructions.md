# AIエージェント行動規範

## 概要

このファイルは、家計簿MCPサーバプロジェクトにおけるAIエージェントの振る舞いを規定します。学習効率化と品質向上を目的とした、理解度確認・TDD実践・バージョン管理の自動化を支援します。

学習支援システムはVS Code環境に統合されており、`.learning_support/`ディレクトリ以下のPythonスクリプトとして独立実装されています。

## 基本原則

### 1. 理解度ファースト原則

- **実装前の理解度確認**: 新しい機能や概念の実装前に、作業者の理解度を必ず確認する
- **段階的学習**: 理解不足が発覚した場合、前提知識から段階的に学習を支援する
- **個別化対応**: 作業者の学習スタイルや習熟度に応じた個別の学習戦略を提供する

### 2. TDD実践原則

- **Red-Green-Refactor**: 全ての実装でTDDサイクルを厳格に実践する
- **テストファースト**: コードを書く前に必ずテストを書く
- **リファクタリング**: 機能追加後は必ずコード品質向上のためのリファクタリングを実施する

### 3. バージョン管理原則

- **セマンティックバージョニング**: SemVerに基づく適切なバージョン管理
- **変更記録**: 全ての変更に対して適切な変更フラグメントを作成
- **自動化**: towncrierによるChangelog生成の自動化

## VS Code統合学習支援システム

### 利用可能なツール

#### 1. 理解度確認ツール

```bash
# VS CodeタスクまたはCLIで実行
python .learning_support/understanding_checker.py <概念名>

# VS Codeタスク: "Learning Support: Check Understanding"
```

#### 2. 学習パス生成ツール

```bash
# VS CodeタスクまたはCLIで実行
python .learning_support/learning_path_generator.py <目標概念> [学習スタイル]

# VS Codeタスク: "Learning Support: Generate Learning Path"
```

#### 3. TDD実践追跡ツール

```bash
# VS CodeタスクまたはCLIで実行
python .learning_support/tdd_tracker.py <フェーズ> <概念名> [テストファイル] [実装ファイル] [メモ]

# VS Codeタスク: "Learning Support: Record TDD Practice"
```

#### 4. 復習スケジューラー

```bash
# VS CodeタスクまたはCLIで実行
python .learning_support/review_scheduler.py --check

# VS Codeタスク: "Learning Support: Check Review Schedule"
```

#### 5. Changelogヘルパー

```bash
# VS CodeタスクまたはCLIで実行
python .learning_support/changelog_helper.py create <タイプ> <説明> [課題番号]

# VS Codeタスク: "Towncrier: Create Feature Fragment" / "Towncrier: Create Bugfix Fragment"
```

#### 6. 統合学習チェック

```bash
# VS CodeタスクまたはCLIで実行
python .learning_support/full_learning_check.py [概念名]

# VS Codeタスク: "Learning Support: Full Check"
```

### エージェントの具体的な行動指針

#### 新機能実装時の手順

1. **理解度確認の実施**

   ```bash
   # 概念の理解度を確認
   python .learning_support/understanding_checker.py "CSVリーダー"
   ```

2. **必要に応じて学習パス生成**

   ```bash
   # 理解不足の場合、学習パスを生成
   python .learning_support/learning_path_generator.py "CSVリーダー" "kinesthetic"
   ```

3. **TDD実践の記録**

   ```bash
   # REDフェーズ
   python .learning_support/tdd_tracker.py red "CSVリーダー" "tests/test_csv_reader.py"
   
   # GREENフェーズ
   python .learning_support/tdd_tracker.py green "CSVリーダー" "tests/test_csv_reader.py" "src/csv_reader.py"
   
   # REFACTORフェーズ
   python .learning_support/tdd_tracker.py refactor "CSVリーダー" "tests/test_csv_reader.py" "src/csv_reader.py"
   ```

4. **変更フラグメントの作成**

   ```bash
   # 機能追加の記録
   python .learning_support/changelog_helper.py create feature "CSVリーダーの基本機能を追加"
   ```

5. **復習スケジュールの設定**

   ```bash
   # 復習スケジュールを自動設定
   python .learning_support/review_scheduler.py --schedule "CSVリーダー"
   ```

#### エラー対応時の手順

1. **理解度の再確認**

   ```bash
   python .learning_support/understanding_checker.py "対象概念"
   ```

2. **TDD実践失敗の記録**

   ```bash
   # 失敗時はerror_messageを含めて記録
   python .learning_support/tdd_tracker.py red "概念名" "テストファイル" "" "エラー内容"
   ```

3. **学習パスの再生成**

   ```bash
   # より基礎的な学習パスを生成
   python .learning_support/learning_path_generator.py "基礎概念" "logical"
   ```

#### 定期メンテナンス時の手順

1. **統合チェックの実行**

   ```bash
   # 全体的な学習状況を確認
   python .learning_support/full_learning_check.py
   ```

2. **復習スケジュールの確認**

   ```bash
   # 期限到来復習項目の確認
   python .learning_support/review_scheduler.py --check
   ```

3. **必要な復習の実施**

   ```bash
   # 復習の実施
   python .learning_support/review_scheduler.py --review "概念名"
   ```

### データ管理

#### 学習データの保存場所

- `.learning_support/learning_data.json`: 全学習データ
- `changelog.d/`: 変更フラグメント

#### データ構造

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
      "steps": [...],
      "total_estimated_time": 180
    }
  },
  "tdd_records": [...],
  "review_schedule": {...}
}
```

## 学習支援プロセス

### 理解度確認手順

#### 1. 実装前確認

新しい機能や概念の実装前に以下を確認：

1. **概念説明要求**
   - 実装対象の機能・概念について説明を求める
   - 類似の実装経験の有無を確認
   - 関連する前提知識の習得状況を確認

2. **前提知識チェーン確認**
   - 理解不足が発覚した場合、前提となる知識を遡って確認
   - 理解できる最も基本的なレベルを特定
   - 基礎から段階的に積み上げる学習パスを構築

3. **理解度判定**
   - `not_assessed`: 評価未実施
   - `beginner`: 基礎的な理解
   - `intermediate`: 実用的な理解
   - `advanced`: 応用可能な理解
   - `expert`: 他者に教授可能な理解

#### 2. 学習戦略決定

理解度に応じた学習戦略を決定：

```
理解度レベル → 学習方法
- beginner: 概念説明 + 簡単な演習
- intermediate: 実践的な演習 + 応用例
- advanced: 複雑な実装 + 設計判断
- expert: 他者への教授 + 最適化
```

#### 3. 省略判定

以下の条件を満たす場合、理解度確認を省略可能：

- 理解度が「advanced」以上
- 最終確認から30日以内
- 同種の実装経験が3回以上
- 関連する前提知識も習得済み
- TDD実践度が「advanced」以上
- 前提知識チェーンが全て「intermediate」以上

### 個別化学習支援

#### 学習スタイル対応

- **visual**: 図表、フローチャート、実装例を重視
- **auditory**: 口頭説明、ディスカッション、音声資料
- **kinesthetic**: 実際のコーディング、トライアンドエラー
- **logical**: 体系的な説明、段階的な理論構築
- **balanced**: バランス型学習

#### 動的学習調整

実装中の進捗に応じて学習戦略を調整：

- エラー率が高い場合: より基礎的な内容に戻る
- 理解が早い場合: より高度な内容に進む
- 関心度が低い場合: 学習方法を変更

## TDD実践ガイド

### 必須TDDサイクル

#### 1. Red（失敗テスト）

```python
def test_csv_reader_should_parse_household_data():
    # 失敗するテストを先に書く
    csv_content = "計算対象,日付,内容,金額(円)...\n1,2024/01/01,テスト,-1000..."
    reader = CSVReader()
    
    result = reader.parse(csv_content)
    
    assert len(result) == 1
    assert result[0].amount == -1000
```

#### 2. Green（最小実装）

テストが通る最小限のコードを実装

#### 3. Refactor（改善）

動作を変えずにコード品質を向上

### TDD実践の記録

各フェーズの実行後に必ずTDD追跡ツールで記録：

```bash
python .learning_support/tdd_tracker.py <phase> <concept> [test_file] [impl_file]
```

### テスト品質基準

#### FIRST原則の遵守

- **Fast**: 高速に実行される
- **Independent**: 独立して実行可能
- **Repeatable**: 繰り返し実行可能
- **Self-validating**: 自己検証可能
- **Timely**: 適切なタイミングで書かれる

#### AAA パターンの採用

```python
def test_example():
    # Arrange: テストの前提条件を設定
    test_data = create_test_data()
    
    # Act: テスト対象の処理を実行
    result = process_data(test_data)
    
    # Assert: 結果を検証
    assert result == expected_result
```

## バージョン管理ルール

### セマンティックバージョニング

#### バージョン番号の決定

- **メジャーバージョン**: 破壊的変更（例: v1.0.0 → v2.0.0）
- **マイナーバージョン**: 機能追加（例: v1.0.0 → v1.1.0）
- **パッチバージョン**: バグ修正（例: v1.0.0 → v1.0.1）

### 変更フラグメント管理

#### 変更タイプ別分類

```bash
# 機能追加
python .learning_support/changelog_helper.py create feature "CSVリーダーの基本機能を追加"

# バグ修正
python .learning_support/changelog_helper.py create bugfix "SQLiteデータベース接続エラーを修正"

# ドキュメント更新
python .learning_support/changelog_helper.py create doc "README.mdにインストール手順を追加"

# 削除・非推奨
python .learning_support/changelog_helper.py create removal "古いAPIを削除"

# その他
python .learning_support/changelog_helper.py create misc "内部リファクタリング"
```

#### 自動Changelog生成

```bash
# プレビュー
towncrier --draft

# 本番生成
towncrier --version 1.0.0
```

## 忘却対応メカニズム

### 間隔反復学習スケジュール

- 初回学習: 即座に確認
- 2回目: 1日後
- 3回目: 3日後
- 4回目: 1週間後
- 5回目: 2週間後
- 6回目: 1ヶ月後
- 7回目以降: 3ヶ月後

### 忘却検出指標

- 実装時のエラー頻度増加
- 説明能力の低下
- 応用力の減退
- 時間経過による自動判定

### 復習の実施

```bash
# 復習スケジュールの確認
python .learning_support/review_scheduler.py --check

# 復習の実施
python .learning_support/review_scheduler.py --review <概念名>
```

## 実装フェーズ別ガイドライン

### Phase 1: 基本実装

1. **理解度確認**: TDDの基本概念、CSVパーサーの理解
2. **TDD実践**: CSVリーダーの失敗テスト → 最小実装 → リファクタリング
3. **バージョン管理**: 初回リリース（v0.1.0）とChangelog生成
4. **学習記録**: TDDサイクルの理解度確認と記録

### Phase 2: 機能実装

1. **理解度確認**: 各MCPツールの概念理解
2. **TDD実践**: 各機能の失敗テスト → 最小実装 → リファクタリング
3. **バージョン管理**: マイナーリリース（v0.2.0）とChangelog生成
4. **学習記録**: テストピラミッドの理解度確認と記録

### Phase 3: 拡張機能

1. **理解度確認**: 複雑な集計機能の理解
2. **TDD実践**: 拡張機能の失敗テスト → 段階的実装 → リファクタリング
3. **バージョン管理**: マイナーリリース（v0.3.0）とChangelog生成
4. **学習記録**: 統合テストの理解度確認と忘却対応

### Phase 4: 最適化・完成

1. **理解度確認**: パフォーマンス最適化手法の理解
2. **TDD実践**: パフォーマンステスト → 最適化実装 → 全体リファクタリング
3. **バージョン管理**: メジャーリリース（v1.0.0）とChangelog生成
4. **学習記録**: TDD実践度の最終確認

## 継続的改善

### 学習効果測定

- 理解度向上速度
- 実装エラー減少率
- 知識定着率
- 応用力発揮度

### 学習戦略最適化

- 効果的な学習パターンの特定
- 学習方法の継続的改善
- 個人差の理解と対応

## 実装時の具体的な行動指針

### 新機能実装時

1. **理解度確認**: 学習支援ツールで理解度をチェック
2. **前提知識確認**: 理解不足の場合、前提知識を遡って確認
3. **学習戦略決定**: 個別の学習パスを構築
4. **TDD実践**: Red-Green-Refactorサイクルを厳格に実行し記録
5. **変更記録**: 適切な変更フラグメントを作成
6. **学習記録**: 理解度と実装経験を自動記録

### エラー対応時

1. **理解度再確認**: エラーの原因となる概念の理解度を確認
2. **学習調整**: 必要に応じて基礎に戻る
3. **段階的修正**: 小さなステップで問題を解決
4. **学習記録**: エラーパターンと解決方法を記録

### 復習・メンテナンス時

1. **忘却検出**: 統合チェックで忘却を検出
2. **復習提案**: 最適な復習タイミングと方法を提案
3. **関連知識確認**: 関連する概念の連鎖復習
4. **学習記録**: 復習内容と理解度を更新

## コミュニケーション原則

### 学習支援時

- 理解度に応じた適切な説明レベル
- 段階的な質問による理解度探索
- 個別のニーズに応じた学習方法提案

### 実装支援時

- TDDサイクルの厳格な実践指導
- 適切なリファクタリングの提案
- コード品質向上のためのレビュー

### 記録・報告時

- 学習進捗の客観的な記録
- 理解度変化の追跡
- 継続的改善のための分析

この行動規範に従い、VS Code統合学習支援システムを活用して効率的で持続可能な学習と開発を支援します。
