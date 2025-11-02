# 利用ガイド

このドキュメントでは、Household MCP Server の主要機能の使用方法を説明します。

## 基本的な使用方法

### 1. 月次サマリーの取得

指定年月の収支サマリーを取得します。

**テキスト形式（デフォルト）**:

```json
{
  "tool": "get_monthly_household",
  "arguments": {
    "year": 2024,
    "month": 10
  }
}
```

**レスポンス**:

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
  }
}
```

### 2. 画像生成（円グラフ）

月次サマリーをグラフとして取得します。

**画像形式リクエスト**:

```json
{
  "tool": "get_monthly_household",
  "arguments": {
    "year": 2024,
    "month": 10,
    "output_format": "image",
    "graph_type": "pie",
    "image_size": "800x600",
    "image_format": "png"
  }
}
```

**レスポンス**:

```json
{
  "success": true,
  "type": "image",
  "url": "http://localhost:8000/api/charts/1a2b3c4d5e6f7g8h...",
  "cache_key": "1a2b3c4d5e6f7g8h...",
  "metadata": {
    "graph_type": "pie",
    "format": "png",
    "size": "800x600",
    "cached": false,
    "timestamp": "2024-10-30T12:34:56Z"
  }
}
```

画像はHTTPエンドポイント（backend の FastAPI サーバ）経由でアクセスできます：

```bash
# ブラウザまたはcurlで画像取得
curl http://localhost:8000/api/charts/1a2b3c4d5e6f7g8h... --output chart.png
```

### 3. カテゴリトレンド分析

特定カテゴリの期間別推移を取得します。

**テキスト形式**:

```json
{
  "tool": "get_category_trend",
  "arguments": {
    "category": "食費",
    "start_month": "2024-01",
    "end_month": "2024-06"
  }
}
```

**レスポンス**:

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
      "year_over_year": -0.05
    },
    {
      "month": "2024-02",
      "amount": -78000,
      "month_over_month": 0.04,
      "year_over_year": -0.02
    }
  ],
  "summary": {
    "average": -76500,
    "max": -80000,
    "min": -72000
  }
}
```

**画像形式（折れ線グラフ）**:

```json
{
  "tool": "get_category_trend",
  "arguments": {
    "category": "食費",
    "start_month": "2024-01",
    "end_month": "2024-12",
    "output_format": "image",
    "graph_type": "line"
  }
}
```

レスポンスは上記の画像生成と同様の形式で返されます。

### 4. カテゴリ一覧の取得

利用可能なカテゴリを検索します。

```json
{
  "tool": "find_categories",
  "arguments": {
    "pattern": "交通"
  }
}
```

**レスポンス**:

```json
{
  "categories": [
    {"name": "交通費", "type": "expense"},
    {"name": "交際費", "type": "expense"}
  ]
}
```

### 5. カテゴリ分析

指定カテゴリの詳細分析を取得します。

```json
{
  "tool": "category_analysis",
  "arguments": {
    "category": "食費",
    "start_month": "2024-01",
    "end_month": "2024-06"
  }
}
```

**レスポンス**:

```json
{
  "category": "食費",
  "period": {
    "start": "2024-01",
    "end": "2024-06"
  },
  "analysis": {
    "total": -450000,
    "average": -75000,
    "max": {"month": "2024-05", "amount": -80000},
    "min": {"month": "2024-02", "amount": -70000},
    "trend": "increasing",
    "month_over_month_avg": 0.03
  }
}
```

## トレンド分析機能の詳細

### 提供される分析指標

#### 1. 前月比（Month over Month: MoM）

前月からの変化率を計算します。

```text
MoM = (当月金額 - 前月金額) / |前月金額|
```

**例**: 前月が -80,000円、当月が -84,000円の場合、MoM = 0.05（5%増加）

#### 2. 前年同月比（Year over Year: YoY）

前年同月からの変化率を計算します。

```text
YoY = (当月金額 - 前年同月金額) / |前年同月金額|
```

**例**: 前年同月が -75,000円、当月が -84,000円の場合、YoY = 0.12（12%増加）

#### 3. 12ヶ月移動平均

直近12ヶ月の平均値を計算し、季節変動を平滑化します。

```text
移動平均 = (直近12ヶ月の合計) / 12
```

トレンドの方向性を把握するのに有効です。

### カテゴリ分析のユースケース

#### ケース1: 月次レポート生成

```python
# 先月と今月の比較
category_analysis(
    start_month="2024-09",
    end_month="2024-10",
    top_n=5
)
```

#### ケース2: 四半期レビュー

```python
# Q3の全体傾向を分析
category_analysis(
    start_month="2024-07",
    end_month="2024-09",
    top_n=10
)
```

#### ケース3: 年次総括

```python
# 年間の支出パターンを確認
category_analysis(
    start_month="2024-01",
    end_month="2024-12",
    top_n=15
)
```

## 画像生成機能の詳細

### サポートされるグラフタイプ

| グラフタイプ | 説明         | 用途                       | 推奨シーン                 |
| ------------ | ------------ | -------------------------- | -------------------------- |
| `pie`        | 円グラフ     | カテゴリ別支出割合の可視化 | 月次サマリー               |
| `line`       | 折れ線グラフ | 時系列トレンドの可視化     | カテゴリトレンド（長期）   |
| `bar`        | 棒グラフ     | カテゴリ間比較             | カテゴリトレンド（短中期） |
| `area`       | 面グラフ     | 累積トレンドの可視化       | 累積支出の推移             |

### 画像サイズオプション

- `800x600` (デフォルト)
- `1024x768`
- `1280x720`
- `1920x1080`

カスタムサイズも `{width}x{height}` 形式で指定可能です。

### 画像フォーマット

- `png` (デフォルト) - 高品質、透過対応
- `svg` - ベクター形式、スケーラブル
- `jpg` - 軽量、写真向け

### キャッシング

画像は自動的にキャッシュされます：

- **TTL**: 600秒（10分）
- **最大サイズ**: 100アイテム
- **キー生成**: パラメータのMD5ハッシュ

キャッシュ統計は以下で確認できます：

```bash
curl http://localhost:8000/api/cache/stats
```

**レスポンス**:

```json
{
  "current_size": 15,
  "max_size": 100,
  "hits": 230,
  "misses": 45,
  "hit_rate": 0.836
}
```

## HTTP エンドポイント

backend の FastAPI アプリ（create_http_app）を起動した場合に利用可能です。

### 画像取得

```http
GET /api/charts/{chart_id}
```

PNG画像をストリーミング配信します（Content-Type: image/png）。

### 画像情報

```http
GET /api/charts/{chart_id}/info
```

**レスポンス**:

```json
{
  "chart_id": "1a2b3c4d...",
  "exists": true,
  "size_bytes": 102400,
  "created_at": "2024-10-30T12:34:56Z"
}
```

### キャッシュクリア

```http
DELETE /api/cache
```

すべてのキャッシュをクリアします。

### ヘルスチェック

```http
GET /health
```

**レスポンス**:

```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

## トラブルシューティング

### 日本語が文字化けする

日本語フォント（Noto Sans CJK JP）がインストールされているか確認してください：

```bash
# fonts/ ディレクトリの確認
ls fonts/NotoSansCJK-*

# フォントがない場合はダウンロード
# 詳細は README.md の「日本語フォント設定」を参照
```

### 画像が生成されない

visualization extras がインストールされているか確認してください：

```bash
uv pip install -e ".[visualization]"

# インストール確認
python -c "from household_mcp.visualization import ChartGenerator; print('OK')"
```

### HTTPエンドポイントが利用できない

streaming または web extras が必要です：

```bash
uv pip install -e ".[streaming]"

# サーバー起動
python -m src.server --transport streamable-http --port 8000
```

## 次のステップ

- [API リファレンス](./api.md) - 詳細なエンドポイント仕様
- [README.md](../README.md) - インストールと設定
- [design.md](../design.md) - 技術設計
