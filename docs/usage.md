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

---

## 資産管理機能

### 概要

資産管理機能では、複数の資産クラス（現金、株式、投信、不動産、年金）の残高を記録・管理し、資産配分分析を行うことができます。

### 基本的な操作

#### 1. 資産レコード登録

Web UI から、資産をアセットクラスごとに登録します。

**操作手順**:

1. ナビゲーションメニューから「💰 資産管理」をクリック
2. 「レコード」タブに移動
3. 「新規追加」フォームで以下を入力:
   - **記録日**: 資産を記録する日（月末推奨）
   - **資産クラス**: 現金、株式、投信、不動産、年金から選択
   - **名前**: 資産の具体的な名前（例: 普通預金、楽天VTI）
   - **金額**: 資産額（JPY）
   - **メモ**: 任意の備考
4. 「追加」ボタンをクリック

**例**:

| 記録日     | 資産クラス | 名前     | 金額      | メモ       |
| ---------- | ---------- | -------- | --------- | ---------- |
| 2025-01-31 | 現金       | 普通預金 | 1,000,000 | 給与振込   |
| 2025-01-31 | 株式       | 楽天VTI  | 500,000   | 米国全市場 |
| 2025-01-31 | 投信       | 投信ABC  | 300,000   | -          |

#### 2. 概要タブで統計確認

「概要」タブでは、以下の統計情報が表示されます:

- **総資産額**: 全資産クラスの合計
- **前月比**: 前月比の増減額
- **最大資産**: 最大単位資産額
- **クラス数**: 登録されているクラス数

また、以下のグラフが表示されます:

- **資産配分（円グラフ）**: 各クラスの割合を視覚化
- **クラス別残高（棒グラフ）**: 各クラスの残高を比較

#### 3. 資産配分分析

「配分」タブで詳細な配分分析を確認:

| 資産クラス | 残高      | 比率   | プログレスバー |
| ---------- | --------- | ------ | -------------- |
| 現金       | 1,000,000 | 55.56% | ▰▰▰▰▰▰▱▱▱▱     |
| 株式       | 500,000   | 27.78% | ▰▰▰▱▱▱▱▱▱▱     |
| 投信       | 300,000   | 16.67% | ▰▰▱▱▱▱▱▱▱▱     |

ドーナツ図でも視覚的に確認できます。

#### 4. CSVエクスポート

「エクスポート」タブから CSV 形式でデータをエクスポート:

**フィルタオプション**:

- **資産クラス**: 特定のクラスのみをエクスポート
- **開始日**: 指定日以降のレコードをエクスポート
- **終了日**: 指定日までのレコードをエクスポート

**ダウンロード形式**:

```csv
record_date,asset_class_name,sub_asset_name,amount,memo
2025-01-31,現金,普通預金,1000000,給与振込
2025-01-31,株式,楽天VTI,500000,
2025-01-31,投信,投信ABC,300000,
```

#### 5. レコード編集・削除

表形式で表示されたレコードを直接編集・削除:

- **編集ボタン**: モーダルダイアログが開き、内容を変更可能
- **削除ボタン**: 確認ダイアログ後、該当レコードを削除（論理削除）

### API を使った操作

REST API からもプログラム的に資産管理を行えます。

#### 資産追加

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

#### 月次サマリー取得

```bash
curl "http://localhost:8000/api/assets/summary?year=2025&month=1"
```

**レスポンス例**:

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

#### 資産配分分析取得

```bash
curl "http://localhost:8000/api/assets/allocation?year=2025&month=1"
```

#### CSV エクスポート

```bash
# 全データをエクスポート
curl "http://localhost:8000/api/assets/export" > assets.csv

# 現金クラスのみ
curl "http://localhost:8000/api/assets/export?asset_class_id=1" > assets_cash.csv

# 特定期間
curl "http://localhost:8000/api/assets/export?start_date=2025-01-01&end_date=2025-01-31" > assets_jan.csv
```

### レスポンシブデザイン

Web UI は以下のデバイスに最適化されています:

- **PC（1024px以上）**: 4つのタブを並行表示、グリッドレイアウト
- **タブレット（768px～1023px）**: 2列表示、調整されたグラフサイズ
- **スマートフォン（480px～767px）**: 1列表示、コンパクトなグラフ、折りたたみ可能なメニュー

すべてのデバイスで以下の機能が利用可能です:

- ✅ データ入力・編集・削除
- ✅ グラフ表示と分析
- ✅ CSV エクスポート
- ✅ リアルタイム検索・フィルタリング

### よくある操作

#### 月末に資産状況を記録

毎月末に、各資産クラスの残高を記録することをお勧めします:

```bash
# 1月末
curl -X POST http://localhost:8000/api/assets/records \
  -H "Content-Type: application/json" \
  -d '{"record_date":"2025-01-31","asset_class_id":1,"sub_asset_name":"普通預金","amount":1000000}'

# 2月末（月初に作成）
curl -X POST http://localhost:8000/api/assets/records \
  -H "Content-Type: application/json" \
  -d '{"record_date":"2025-02-28","asset_class_id":1,"sub_asset_name":"普通預金","amount":1200000}'
```

#### 複数月の推移を確認

複数月のデータを記録した後、CSV エクスポートで一覧表示:

```bash
curl "http://localhost:8000/api/assets/export?asset_class_id=1" > cash_history.csv
```

#### トレンド分析

配分タブで各月の資産配分の推移を確認し、投資戦略の見直しに活用できます。

### トラブルシューティング

#### グラフが表示されない

- ブラウザコンソール（F12）でエラーを確認
- Chart.js ライブラリが読み込まれているか確認
- キャッシュをクリア（Ctrl+Shift+Delete）

#### API が 404 エラーを返す

- API サーバーが起動していることを確認
- `http://localhost:8000/api/assets/classes` でエンドポイント確認
- ポート番号が正しいか確認

#### レコード登録後に表示されない

- リロード（F5）してキャッシュをクリア
- ブラウザコンソールでエラーを確認
- 日付フォーマットが YYYY-MM-DD か確認

---

## 次のステップ（資産管理機能）

- [API リファレンス](./api.md) - 詳細なエンドポイント仕様
- [README.md](../README.md) - インストールと設定
- [design.md](../design.md) - 技術設計
