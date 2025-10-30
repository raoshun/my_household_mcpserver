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

HTTPストリーミングモード（`--transport streamable-http`）で起動した場合に利用可能です。

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
