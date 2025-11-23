# API仕様

このドキュメントでは、Household MCP Server が提供する MCP ツール/リソースと HTTP エンドポイントの詳細を説明します。

## MCP ツール

### get_monthly_household

指定年月の家計簿データを取得します。

**パラメータ**:

| 名前            | 型        | 必須 | デフォルト  | 説明                                               |
| --------------- | --------- | ---- | ----------- | -------------------------------------------------- |
| `year`          | `integer` | ✓    | -           | 取得年（YYYY）                                     |
| `month`         | `integer` | ✓    | -           | 取得月（1-12）                                     |
| `output_format` | `string`  | -    | `"text"`    | 出力形式: `"text"` または `"image"`                |
| `graph_type`    | `string`  | -    | `"pie"`     | グラフタイプ: `"pie"`, `"bar"`, `"line"`, `"area"` |
| `image_size`    | `string`  | -    | `"800x600"` | 画像サイズ（例: `"1024x768"`）                     |
| `image_format`  | `string`  | -    | `"png"`     | 画像フォーマット: `"png"`, `"svg"`, `"jpg"`        |

**レスポンス（text形式）**:

```json
{
  "year": 2024,
  "month": 10,
  "summary": {
    "total_income": 300000,
    "total_expense": -250000,
    "balance": 50000,
    "top_categories": [
      {"category": "食費", "amount": -80000},
      {"category": "交通費", "amount": -30000}
    ]
  },
  "transactions": [
    {
      "date": "2024-10-01",
      "category": "食費",
      "sub_category": "外食",
      "amount": -1500,
      "description": "ランチ"
    }
  ]
}
```

**レスポンス（image形式）**:

```json
{
  "success": true,
  "type": "image",
  "url": "http://localhost:8000/api/charts/1a2b3c4d5e6f...",
  "cache_key": "1a2b3c4d5e6f...",
  "metadata": {
    "graph_type": "pie",
    "format": "png",
    "size": "800x600",
    "cached": false,
    "generated_at": "2024-10-30T12:34:56Z"
  }
}
```

---

### get_category_trend

カテゴリ別のトレンド分析を取得します。

**パラメータ**:

| 名前            | 型       | 必須 | デフォルト   | 説明                                 |
| --------------- | -------- | ---- | ------------ | ------------------------------------ |
| `category`      | `string` | -    | -            | カテゴリ名（未指定時は上位カテゴリ） |
| `start_month`   | `string` | -    | 直近12ヶ月前 | 開始月（YYYY-MM）                    |
| `end_month`     | `string` | -    | 今月         | 終了月（YYYY-MM）                    |
| `output_format` | `string` | -    | `"text"`     | 出力形式: `"text"` または `"image"`  |
| `graph_type`    | `string` | -    | `"line"`     | グラフタイプ                         |
| `image_size`    | `string` | -    | `"800x600"`  | 画像サイズ                           |
| `image_format`  | `string` | -    | `"png"`      | 画像フォーマット                     |

**レスポンス（text形式）**:

```json
{
  "category": "食費",
  "start_month": "2024-01",
  "end_month": "2024-06",
  "metrics": [
    {
      "month": "2024-01",
      "amount": -75000,
      "month_over_month": null,
      "year_over_year": -0.05,
      "moving_average_12m": -74500
    }
  ],
  "summary": {
    "total": -450000,
    "average": -75000,
    "max": {"month": "2024-05", "amount": -80000},
    "min": {"month": "2024-02", "amount": -70000}
  }
}
```

**レスポンス（image形式）**:

画像形式の場合、`get_monthly_household` と同様の構造で画像URLを返します。

---

### category_analysis

カテゴリの詳細分析を取得します。

**パラメータ**:

| 名前          | 型       | 必須 | デフォルト | 説明              |
| ------------- | -------- | ---- | ---------- | ----------------- |
| `category`    | `string` | ✓    | -          | 分析対象カテゴリ  |
| `start_month` | `string` | ✓    | -          | 開始月（YYYY-MM） |
| `end_month`   | `string` | ✓    | -          | 終了月（YYYY-MM） |

**レスポンス**:

```json
{
  "category": "食費",
  "period": {
    "start": "2024-01",
    "end": "2024-06",
    "months": 6
  },
  "analysis": {
    "total": -450000,
    "average": -75000,
    "max": {"month": "2024-05", "amount": -80000},
    "min": {"month": "2024-02", "amount": -70000},
    "trend": "increasing",
    "month_over_month_avg": 0.03,
    "year_over_year_avg": -0.02
  }
}
```

---

### find_categories

カテゴリ名で検索します。

**パラメータ**:

| 名前      | 型       | 必須 | デフォルト | 説明                     |
| --------- | -------- | ---- | ---------- | ------------------------ |
| `pattern` | `string` | -    | `""`       | 検索パターン（部分一致） |

**レスポンス**:

```json
{
  "categories": [
    {"name": "食費", "type": "expense", "count": 456},
    {"name": "交通費", "type": "expense", "count": 234}
  ],
  "total": 2
}
```

---

### monthly_summary

月次サマリーを取得します。

**パラメータ**:

| 名前    | 型        | 必須 | デフォルト | 説明   |
| ------- | --------- | ---- | ---------- | ------ |
| `year`  | `integer` | ✓    | -          | 対象年 |
| `month` | `integer` | ✓    | -          | 対象月 |

**レスポンス**:

```json
{
  "year": 2024,
  "month": 10,
  "income": {
    "total": 300000,
    "categories": [
      {"category": "給与", "amount": 300000}
    ]
  },
  "expense": {
    "total": -250000,
    "categories": [
      {"category": "食費", "amount": -80000},
      {"category": "交通費", "amount": -30000}
    ]
  },
  "balance": 50000
}
```

---

### get_financial_independence_status

経済的自由（FIRE）への進捗状況を取得します。

**パラメータ**:

| 名前            | 型        | 必須 | デフォルト | 説明                   |
| --------------- | --------- | ---- | ---------- | ---------------------- |
| `period_months` | `integer` | -    | 12         | 分析対象期間（月数）   |

**レスポンス**:

```json
{
  "current_assets": 5000000,
  "target_assets": 60000000,
  "progress_rate": 8.33,
  "annual_expense": 2400000,
  "months_to_fi": 120,
  "monthly_growth_rate": 0.005,
  "trend": "stable"
}
```

---

### analyze_expense_patterns

支出パターン（定常・臨時）を分析します。

**パラメータ**:

| 名前            | 型        | 必須 | デフォルト | 説明                   |
| --------------- | --------- | ---- | ---------- | ---------------------- |
| `period_months` | `integer` | -    | 12         | 分析対象期間（月数）   |
| `category`      | `string`  | -    | -          | 特定カテゴリ（省略可） |

**レスポンス**:

```json
{
  "regular_spending": 200000,
  "irregular_spending": 50000,
  "categories": [
    {
      "category": "食費",
      "classification": "regular",
      "average_amount": 50000,
      "confidence": 0.9
    }
  ]
}
```

---

### project_financial_independence_date

FIRE達成予定日を予測します。

**パラメータ**:

| 名前                           | 型        | 必須 | デフォルト | 説明                   |
| ------------------------------ | --------- | ---- | ---------- | ---------------------- |
| `additional_savings_per_month` | `integer` | -    | 0          | 追加貯蓄額（月額）     |
| `custom_growth_rate`           | `number`  | -    | -          | カスタム成長率（月利） |

**レスポンス**:

```json
{
  "current_projection": {
    "months_to_fi": 120,
    "target_date": "2035-01"
  },
  "improved_projection": {
    "months_to_fi": 100,
    "target_date": "2033-05"
  },
  "improvement": {
    "months_saved": 20,
    "years_saved": 1.7
  }
}
```

---

### suggest_improvement_actions

家計改善アクションを提案します。

**パラメータ**:

| 名前             | 型        | 必須 | デフォルト | 説明                   |
| ---------------- | --------- | ---- | ---------- | ---------------------- |
| `annual_expense` | `integer` | -    | -          | 年間支出額（省略可）   |

**レスポンス**:

```json
{
  "suggestions": [
    {
      "priority": "HIGH",
      "type": "reduction",
      "title": "固定費の見直し",
      "description": "通信費が高い傾向にあります...",
      "impact": 5000
    }
  ]
}
```

---

### compare_scenarios

複数シナリオを比較します。

**パラメータ**:

| 名前               | 型     | 必須 | デフォルト | 説明                   |
| ------------------ | ------ | ---- | ---------- | ---------------------- |
| `scenario_configs` | `dict` | -    | -          | シナリオ設定（省略可） |

**レスポンス**:

```json
{
  "scenarios": [
    {
      "name": "Current",
      "months_to_fi": 120
    },
    {
      "name": "Aggressive Savings",
      "months_to_fi": 100
    }
  ]
}
```

---

### register_fire_snapshot

資産スナップショットを登録します。

**パラメータ**:

| 名前                | 型        | 必須 | デフォルト | 説明                   |
| ------------------- | --------- | ---- | ---------- | ---------------------- |
| `snapshot_date`     | `string`  | ✓    | -          | 日付（YYYY-MM-DD）     |
| `cash_and_deposits` | `integer` | -    | 0          | 現金・預金             |
| `stocks_cash`       | `integer` | -    | 0          | 株式（現物）           |
| `stocks_margin`     | `integer` | -    | 0          | 株式（信用）           |
| `investment_trusts` | `integer` | -    | 0          | 投資信託               |
| `pension`           | `integer` | -    | 0          | 年金                   |
| `points`            | `integer` | -    | 0          | ポイント               |
| `notes`             | `string`  | -    | -          | 備考                   |

**レスポンス**:

```json
{
  "status": "success",
  "message": "スナップショットを登録しました",
  "data": { ... }
}
```

---

### get_annual_expense_breakdown

年間支出の内訳を取得します。

**パラメータ**:

| 名前   | 型        | 必須 | デフォルト | 説明                   |
| ------ | --------- | ---- | ---------- | ---------------------- |
| `year` | `integer` | -    | 直近1年    | 対象年（YYYY）         |

**レスポンス**:

```json
{
  "period": "2024年",
  "total_annual_expense": 3000000,
  "monthly_breakdown": [...],
  "category_breakdown": [...]
}
```

---

### compare_actual_vs_fire_target

実支出とFIRE目標支出を比較します。

**パラメータ**:

| 名前            | 型        | 必須 | デフォルト | 説明                   |
| --------------- | --------- | ---- | ---------- | ---------------------- |
| `period_months` | `integer` | -    | 12         | 分析対象期間（月数）   |

**レスポンス**:

```json
{
  "actual_annual_expense": 3000000,
  "fire_based_expense": 2400000,
  "difference": 600000,
  "expense_ratio": 1.25
}
```

---

## MCP リソース

### data://category_hierarchy

カテゴリ階層辞書（大項目→中項目）を返します。

**レスポンス**:

```json
{
  "食費": ["外食", "食材", "飲料"],
  "交通費": ["電車", "バス", "タクシー"],
  "娯楽費": ["書籍", "映画", "趣味"]
}
```

---

### data://available_months

利用可能な年月のリストを返します。

**レスポンス**:

```json
{
  "months": [
    "2022-01", "2022-02", "2022-03",
    "2024-10", "2024-11", "2024-12"
  ],
  "count": 36,
  "earliest": "2022-01",
  "latest": "2024-12"
}
```

---

### data://category_trend_summary

直近12ヶ月のカテゴリ別トレンドサマリーを返します。

**レスポンス**:

```json
{
  "period": {
    "start": "2023-11",
    "end": "2024-10"
  },
  "trends": {
    "食費": {
      "average": -75000,
      "trend": "stable",
      "month_over_month_avg": 0.01
    },
    "交通費": {
      "average": -30000,
      "trend": "decreasing",
      "month_over_month_avg": -0.05
    }
  }
}
```

---

## HTTP エンドポイント

HTTP API は FastAPI アプリ（`household_mcp.web.http_server:create_http_app`）を Uvicorn で起動すると利用できます。

起動例（backend/ にて）:

```bash
uv run python -m uvicorn household_mcp.web.http_server:create_http_app \
  --factory --reload --host 0.0.0.0 --port 8000
```

### GET /api/charts/{chart_id}

画像を取得します（ストリーミング配信）。

**パス パラメータ**:

- `chart_id`: 画像識別子（MD5ハッシュ、32文字）

**レスポンス**:

- **Content-Type**: `image/png`, `image/svg+xml`, または `image/jpeg`
- **ステータスコード**:

  - `200 OK`: 画像が正常に返却
  - `404 Not Found`: 画像が存在しない

**例**:

```bash
curl -O http://localhost:8000/api/charts/1a2b3c4d5e6f7g8h...
```

---

### GET /api/charts/{chart_id}/info

画像のメタデータを取得します。

**パス パラメータ**:

- `chart_id`: 画像識別子

**レスポンス**:

```json
{
  "chart_id": "1a2b3c4d5e6f...",
  "exists": true,
  "size_bytes": 102400,
  "format": "png",
  "created_at": "2024-10-30T12:34:56Z",
  "ttl_seconds": 450
}
```

**ステータスコード**:

- `200 OK`: メタデータ返却
- `404 Not Found`: 画像が存在しない

---

### GET /api/cache/stats

キャッシュ統計情報を取得します。

**レスポンス**:

```json
{
  "current_size": 15,
  "max_size": 100,
  "hit_rate": 0.836,
  "hits": 230,
  "misses": 45,
  "total_requests": 275
}
```

**ステータスコード**:

- `200 OK`: 統計情報返却

---

### DELETE /api/cache

すべてのキャッシュをクリアします。

**レスポンス**:

```json
{
  "success": true,
  "cleared_items": 15,
  "message": "Cache cleared successfully"
}
```

**ステータスコード**:

- `200 OK`: キャッシュクリア成功

---

### GET /health

サーバーのヘルスチェックを実行します。

**レスポンス**:

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2024-10-30T12:34:56Z"
}
```

**ステータスコード**:

- `200 OK`: サーバー正常

---

## エラーレスポンス

すべてのHTTPエンドポイントは、エラー時に以下の形式でレスポンスを返します：

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "エラーメッセージ",
    "details": {
      "additional": "information"
    }
  }
}
```

**共通エラーコード**:

| コード                       | 説明                                |
| ---------------------------- | ----------------------------------- |
| `CHART_NOT_FOUND`            | 指定された画像が存在しない          |
| `INVALID_PARAMETERS`         | 無効なパラメータ                    |
| `VISUALIZATION_DEPS_MISSING` | visualization extras 未インストール |
| `INTERNAL_ERROR`             | サーバー内部エラー                  |

---

## キャッシング戦略

画像は以下の戦略でキャッシュされます：

- **キー生成**: パラメータのMD5ハッシュ（32文字）
- **TTL**: 600秒（10分）
- **最大サイズ**: 100アイテム
- **削除ポリシー**: LRU（Least Recently Used）

同じパラメータでのリクエストは、キャッシュから即座に返却されます（NFR-005: <3秒を大幅に下回る）。

---

## パフォーマンス特性

### NFR-005: 画像生成時間

- **目標**: < 3秒
- **実測値**:
  - 円グラフ: 0.234秒
  - 折れ線グラフ: 0.160秒
  - 棒グラフ: 0.154秒
- **キャッシュヒット時**: < 0.1秒

### NFR-006: メモリ使用量

- **目標**: < 50MB
- **実測値**: 増分 1.25MB（大規模データセット100カテゴリ）

詳細は `PROGRESS.md` の TASK-607 を参照してください。

---

## 資産管理 API

### 概要

資産管理 API は、複数の資産クラス（現金、株式、投信、不動産、年金）の残高を管理し、資産配分分析と時系列トレンド分析を提供します。

**ベースURL**: `http://localhost:8000/api/assets/`

### エンドポイント一覧

| メソッド | パス            | 説明                         |
| -------- | --------------- | ---------------------------- |
| POST     | `/records`      | 資産レコード追加             |
| GET      | `/records`      | 資産レコード一覧取得         |
| PUT      | `/records/{id}` | 資産レコード更新             |
| DELETE   | `/records/{id}` | 資産レコード削除（論理削除） |
| GET      | `/summary`      | 月次サマリー取得             |
| GET      | `/allocation`   | 資産配分分析取得             |
| GET      | `/export`       | CSV エクスポート             |
| GET      | `/classes`      | 資産クラス一覧取得           |

### データモデル

#### AssetClass

```json
{
  "id": 1,
  "name": "cash",
  "display_name": "現金"
}
```

**固定クラス**:

- `1`: cash（現金）
- `2`: stocks（株式）
- `3`: funds（投信）
- `4`: realestate（不動産）
- `5`: pension（年金）

#### AssetRecord

```json
{
  "id": 1,
  "record_date": "2025-01-31",
  "asset_class_id": 1,
  "asset_class_name": "現金",
  "sub_asset_name": "普通預金",
  "amount": 1000000,
  "memo": "給与振込",
  "created_at": "2025-01-31T12:00:00",
  "deleted_at": null
}
```

### エンドポイント詳細

#### 1. レコード追加: POST /records

新しい資産レコードを追加します。

**リクエストボディ**:

```json
{
  "record_date": "2025-01-31",
  "asset_class_id": 1,
  "sub_asset_name": "普通預金",
  "amount": 1000000,
  "memo": "給与振込"
}
```

**レスポンス（201 Created）**:

```json
{
  "id": 1,
  "record_date": "2025-01-31",
  "asset_class_id": 1,
  "asset_class_name": "現金",
  "sub_asset_name": "普通預金",
  "amount": 1000000,
  "memo": "給与振込",
  "created_at": "2025-01-31T12:00:00",
  "deleted_at": null
}
```

**使用例**:

```bash
curl -X POST http://localhost:8000/api/assets/records \
  -H "Content-Type: application/json" \
  -d '{
    "record_date": "2025-01-31",
    "asset_class_id": 1,
    "sub_asset_name": "普通預金",
    "amount": 1000000,
    "memo": "給与振込"
  }'
```

#### 2. レコード一覧: GET /records

資産レコード一覧を取得します。

**クエリパラメータ**:

| パラメータ       | 型      | 説明                                 |
| ---------------- | ------- | ------------------------------------ |
| `asset_class_id` | integer | 資産クラスID（オプション）           |
| `start_date`     | string  | 開始日（YYYY-MM-DD形式、オプション） |
| `end_date`       | string  | 終了日（YYYY-MM-DD形式、オプション） |

**レスポンス（200 OK）**:

```json
[
  {
    "id": 1,
    "record_date": "2025-01-31",
    "asset_class_id": 1,
    "asset_class_name": "現金",
    "sub_asset_name": "普通預金",
    "amount": 1000000,
    "memo": "給与振込",
    "created_at": "2025-01-31T12:00:00",
    "deleted_at": null
  }
]
```

**使用例**:

```bash
# 全レコード取得
curl http://localhost:8000/api/assets/records

# 現金クラスのレコード取得
curl http://localhost:8000/api/assets/records?asset_class_id=1

# 日付範囲指定
curl "http://localhost:8000/api/assets/records?start_date=2025-01-01&end_date=2025-01-31"
```

#### 3. レコード更新: PUT /records/{id}

既存の資産レコードを更新します。

**パスパラメータ**:

- `id` (integer): レコードID

**リクエストボディ**: AssetRecordRequest と同じ

**レスポンス（200 OK）**: 更新後のレコード

**使用例**:

```bash
curl -X PUT http://localhost:8000/api/assets/records/1 \
  -H "Content-Type: application/json" \
  -d '{
    "record_date": "2025-02-28",
    "asset_class_id": 1,
    "sub_asset_name": "定期預金",
    "amount": 1500000,
    "memo": "更新テスト"
  }'
```

#### 4. レコード削除: DELETE /records/{id}

資産レコードを削除します（論理削除）。

**パスパラメータ**:

- `id` (integer): レコードID

**レスポンス（204 No Content）**: 削除成功

**使用例**:

```bash
curl -X DELETE http://localhost:8000/api/assets/records/1
```

#### 5. 月次サマリー: GET /summary

指定月の資産サマリーを取得します。

**クエリパラメータ**:

| パラメータ | 型      | 必須 | 説明           |
| ---------- | ------- | ---- | -------------- |
| `year`     | integer | ✓    | 対象年（YYYY） |
| `month`    | integer | ✓    | 対象月（1-12） |

**レスポンス（200 OK）**:

```json
{
  "year": 2025,
  "month": 1,
  "date": "2025-01-31",
  "total_balance": 1800000,
  "summary": [
    {
      "asset_class_id": 1,
      "asset_class_name": "現金",
      "balance": 1000000,
      "record_count": 1
    },
    {
      "asset_class_id": 2,
      "asset_class_name": "株式",
      "balance": 500000,
      "record_count": 1
    },
    {
      "asset_class_id": 3,
      "asset_class_name": "投信",
      "balance": 300000,
      "record_count": 1
    }
  ]
}
```

**使用例**:

```bash
curl "http://localhost:8000/api/assets/summary?year=2025&month=1"
```

#### 6. 資産配分分析: GET /allocation

指定月の資産配分分析を取得します。

**クエリパラメータ**: サマリーと同じ

**レスポンス（200 OK）**:

```json
{
  "year": 2025,
  "month": 1,
  "date": "2025-01-31",
  "total_assets": 1800000,
  "allocations": [
    {
      "asset_class_id": 1,
      "asset_class_name": "現金",
      "balance": 1000000,
      "percentage": 55.56
    },
    {
      "asset_class_id": 2,
      "asset_class_name": "株式",
      "balance": 500000,
      "percentage": 27.78
    },
    {
      "asset_class_id": 3,
      "asset_class_name": "投信",
      "balance": 300000,
      "percentage": 16.67
    }
  ]
}
```

**使用例**:

```bash
curl "http://localhost:8000/api/assets/allocation?year=2025&month=1"
```

#### 7. CSV エクスポート: GET /export

資産レコードを CSV 形式でエクスポートします。

**クエリパラメータ**:

| パラメータ       | 型      | 説明                                 |
| ---------------- | ------- | ------------------------------------ |
| `asset_class_id` | integer | 資産クラスID（オプション）           |
| `start_date`     | string  | 開始日（YYYY-MM-DD形式、オプション） |
| `end_date`       | string  | 終了日（YYYY-MM-DD形式、オプション） |

**レスポンス（200 OK）**:

```text
record_date,asset_class_name,sub_asset_name,amount,memo
2025-01-31,現金,普通預金,1000000,給与振込
2025-01-31,株式,楽天VTI,500000,
2025-01-31,投信,投信ABC,300000,
```

**レスポンスヘッダ**:

- `Content-Type: text/csv; charset=utf-8`
- `Content-Disposition: attachment; filename=assets_export.csv`

**使用例**:

```bash
# 全レコードをCSVでダウンロード
curl http://localhost:8000/api/assets/export > assets.csv

# 現金クラスのみをエクスポート
curl "http://localhost:8000/api/assets/export?asset_class_id=1" > assets_cash.csv

# 特定期間をエクスポート
curl "http://localhost:8000/api/assets/export?start_date=2025-01-01&end_date=2025-01-31" > assets_jan.csv
```

#### 8. 資産クラス一覧: GET /classes

利用可能な資産クラス一覧を取得します。

**レスポンス（200 OK）**:

```json
[
  {"id": 1, "name": "cash", "display_name": "現金"},
  {"id": 2, "name": "stocks", "display_name": "株式"},
  {"id": 3, "name": "funds", "display_name": "投信"},
  {"id": 4, "name": "realestate", "display_name": "不動産"},
  {"id": 5, "name": "pension", "display_name": "年金"}
]
```

**使用例**:

```bash
curl http://localhost:8000/api/assets/classes
```

### エラーレスポンス例

#### 400 Bad Request - 無効なパラメータ

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["query", "year"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

#### 404 Not Found - レコード見つからない

```json
{
  "detail": "Record not found"
}
```

#### 422 Unprocessable Entity - 検証エラー

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "amount"],
      "msg": "Amount must be positive",
      "input": {"amount": -1000}
    }
  ]
}
```

### パフォーマンス特性

**NFR-022**: API レスポンスタイム < 1秒

- GET /records: 50-150ms（1000件）
- GET /summary: 80-200ms
- GET /allocation: 100-250ms
- POST /records: 50-150ms
- PUT /records/{id}: 50-150ms
- DELETE /records/{id}: 50-100ms
- GET /export: 200-500ms（1000件CSV生成含む）

**NFR-023**: グラフ生成 < 3秒

- フロントエンド Chart.js 描画: 100-300ms（1000+ 月次データ）

**NFR-024**: 大規模データセット処理

- 1000件で月次集計: < 1秒
- メモリ使用量: < 50MB（増分）
