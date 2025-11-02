# 重複レコード検出機能 - ユーザーガイド

## 概要

家計簿の重複取引を検出・解消するためのMCPツール群です。会話形式でAIと対話しながら、直感的に重複レコードを管理できます。

## 提供されるMCPツール

### 必須ツール(会話の流れに沿った3ツール)

#### 1. `detect_duplicates` - 重複検出の起点

**使用例の会話:**

- 「重複している取引を見つけて」
- 「同じ支出が二重に登録されていないか確認して」

**パラメータ:**

```typescript
{
  date_tolerance_days?: number;      // 日付の誤差許容(±日数、デフォルト: 0)
  amount_tolerance_abs?: number;     // 金額の絶対誤差(±円、デフォルト: 0)
  amount_tolerance_pct?: number;     // 金額の割合誤差(±%、デフォルト: 0)
  min_similarity_score?: number;     // 最小類似度(0.0-1.0、デフォルト: 0.8)
}
```

**返却値:**

```json
{
  "success": true,
  "detected_count": 5,
  "message": "5件の重複候補を検出しました"
}
```

---

#### 2. `get_duplicate_candidates` - 候補の確認

**使用例の会話:**

- 「重複候補を見せて」
- 「次の重複候補は?」
- 「最初の3件だけ見せて」

**パラメータ:**

```typescript
{
  limit?: number;  // 取得件数(デフォルト: 10)
}
```

**返却値:**

```json
{
  "success": true,
  "count": 2,
  "candidates": [
    {
      "check_id": 1,
      "transaction1": {
        "id": 123,
        "date": "2025-01-15",
        "amount": -5000,
        "description": "スーパーマーケット",
        "category": "食費"
      },
      "transaction2": {
        "id": 124,
        "date": "2025-01-15",
        "amount": -5000,
        "description": "スーパー",
        "category": "食費"
      },
      "similarity_score": 0.95
    }
  ]
}
```

---

#### 3. `confirm_duplicate` - 判定の記録

**使用例の会話:**

- 「これは重複です」 → `decision="duplicate"`
- 「これは別の取引です」 → `decision="not_duplicate"`
- 「後で判断する」 → `decision="skip"`

**パラメータ:**

```typescript
{
  check_id: number;    // 重複候補のチェックID
  decision: "duplicate" | "not_duplicate" | "skip";
}
```

**返却値:**

```json
{
  "success": true,
  "message": "重複として記録しました。取引ID 124を集計から除外します。"
}
```

---

### オプションツール(状況に応じて)

#### 4. `restore_duplicate` - 誤判定の修正

**使用例の会話:**

- 「さっきの判定は間違えた。復元して」
- 「取引ID 124を復元して」

**パラメータ:**

```typescript
{
  transaction_id: number;  // 復元する取引のID
}
```

**返却値:**

```json
{
  "success": true,
  "message": "取引ID 124を復元しました。集計に再度含まれます。"
}
```

---

#### 5. `get_duplicate_stats` - 統計情報

**使用例の会話:**

- 「重複はどれくらいある?」
- 「重複の状況を教えて」

**パラメータ:** なし

**返却値:**

```json
{
  "success": true,
  "stats": {
    "total_candidates": 10,
    "confirmed_duplicates": 5,
    "confirmed_not_duplicates": 3,
    "pending": 2,
    "total_amount_excluded": 25000
  }
}
```

---

## 典型的な会話フロー

### シナリオ1: 完全一致の重複検出

```text
ユーザー: 「重複している取引を見つけて」
AI: detect_duplicates() を実行
    → 「3件の重複候補を検出しました」

ユーザー: 「重複候補を見せて」
AI: get_duplicate_candidates(limit=10) を実行
    → 候補リストを表示

ユーザー: 「最初のやつは重複です」
AI: confirm_duplicate(check_id=1, decision="duplicate") を実行
    → 「重複として記録しました」

ユーザー: 「2番目は別の取引です」
AI: confirm_duplicate(check_id=2, decision="not_duplicate") を実行
    → 「別の取引として記録しました」
```

### シナリオ2: 誤差許容での検出

```text
ユーザー: 「日付が±1日ずれてるかもしれない重複を探して」
AI: detect_duplicates(date_tolerance_days=1) を実行
    → 「7件の重複候補を検出しました」

ユーザー: 「候補を見せて」
AI: get_duplicate_candidates() を実行
    → 候補リスト表示

ユーザー: 「1番目は重複です」
AI: confirm_duplicate(check_id=1, decision="duplicate")

ユーザー: 「あ、間違えた。取引ID 456を復元して」
AI: restore_duplicate(transaction_id=456)
    → 「復元しました」
```

### シナリオ3: 状況確認

```text
ユーザー: 「重複はどれくらいある?」
AI: get_duplicate_stats() を実行
    → 統計情報を表示

ユーザー: 「未判定の候補を見せて」
AI: get_duplicate_candidates() を実行
    → 未判定の候補のみ表示
```

---

## 重要な仕様

### データ永続化

- 判定結果はSQLiteデータベース(`data/household.db`)に保存
- サーバー再起動後も判定結果は保持される
- 重複と判定された取引は**論理削除**(物理削除しない)

### 集計への影響

- `is_duplicate=True`の取引はデフォルトで集計から除外
- 復元(`restore_duplicate`)すると再び集計に含まれる
- 監査・検証用に重複を含めた分析も可能(オプション)

### 検出ロジック

- **日付と金額**に基づいて重複候補を検出
- 摘要・カテゴリは判定基準に含めない(参考情報として表示)
- 類似度スコアで候補の信頼性を評価

---

## トラブルシューティング

### Q: 検出されない重複がある

A: 誤差許容パラメータを調整してください:

```python
detect_duplicates(
  date_tolerance_days=1,      // ±1日の誤差を許容
  amount_tolerance_abs=100,   // ±100円の誤差を許容
  amount_tolerance_pct=1      // ±1%の誤差を許容
)
```

### Q: 誤って重複と判定してしまった

A: `restore_duplicate`で復元できます:

```python
restore_duplicate(transaction_id=123)
```

### Q: 判定を保留したい

A: `decision="skip"`を使用:

```python
confirm_duplicate(check_id=1, decision="skip")
```

---

## 実装詳細

- **ファイル構成:**
  - `backend/src/household_mcp/duplicate/detector.py` - 検出エンジン
  - `backend/src/household_mcp/duplicate/service.py` - ビジネスロジック
  - `backend/src/household_mcp/tools/duplicate_tools.py` - MCPツール関数
  - `backend/src/household_mcp/server.py` - MCPツール登録

- **データベーススキーマ:**
  - `transactions.is_duplicate` - 重複フラグ
  - `transactions.duplicate_of` - 参照先取引ID
  - `duplicate_checks` - 重複候補と判定履歴

---

## 参考資料

- [要件定義書](../requirements.md) - FR-009
- [設計仕様書](../design.md)
- [テストコード](../backend/tests/test_duplicate_tools.py)
