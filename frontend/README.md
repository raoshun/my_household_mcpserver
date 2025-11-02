# 家計簿分析 Webフロントエンド（frontend/）

HTTP API サーバ（FastAPI）と通信して家計簿をインタラクティブに操作できる静的Webアプリです。Vanilla JS + Chart.js 構成でビルド不要。

## 📋 概要

このWebアプリは、Household Budget MCP Server の HTTP API と通信し、家計簿データの可視化と分析を行います。

### 主な機能

- ✅ 月次データの表示と分析
- ✅ インタラクティブなグラフ表示（円/棒/折れ線）
- ✅ データテーブルの表示と検索・フィルタリング
- ✅ 概要統計（総支出、取引件数、平均支出、最大支出）
- ✅ レスポンシブデザイン（モバイル対応）

## 🏗️ 構成

```text
frontend/
├── index.html           # メインページ（分析/トレンド）
├── duplicates.html      # 重複検出UI
├── css/
│   ├── style.css        # 共通スタイル
│   └── duplicates.css   # 重複検出ページ用スタイル
└── js/
    ├── api.js           # APIクライアント
    ├── chart.js         # チャート管理
    ├── trend.js         # トレンド分析管理
    └── main.js          # アプリエントリ
```

## 🚀 起動手順（リポジトリルートから）

### 1) バックエンドAPIの起動（port 8000）

- VS Code タスク:
  - 「Start HTTP API Server」
- もしくは手動（ドキュメント用）:

```bash
uv -C backend run python -m uvicorn household_mcp.web.http_server:create_http_app --factory --reload --host 0.0.0.0 --port 8000
```

APIが起動すると以下が有効になります：

- <http://localhost:8000>
- <http://localhost:8000/docs>

### 2) フロントエンドの配信（port 8080）

- VS Code タスク:
  - 「Start Webapp HTTP Server」
- もしくは手動:

```bash
cd frontend
python3 -m http.server 8080
```

ブラウザで <http://localhost:8080> を開いてください。

### 3) フルスタック同時起動

- VS Code タスク: 「Start Full Webapp Stack」
  - backend(8000) + frontend(8080) を並行起動

## 🔌 API の主なエンドポイント

- GET /api/available-months: 利用可能な年月一覧
- GET /api/monthly: 月次データ（グラフ/テーブル用）
- GET /api/category-hierarchy: カテゴリ階層
- GET /api/trend/monthly_summary: 月次サマリー（収入/支出/差額, トレンド）
- GET /api/trend/category_breakdown: カテゴリ別推移（上位N）
- GET /health: ヘルスチェック

API URL は `js/api.js` 内の `API_BASE_URL` で変更できます：

```js
const API_BASE_URL = 'http://localhost:8000';
```

## 🎨 カスタマイズ

カラーテーマは `css/style.css` の CSS 変数から調整できます：

```css
:root {
  --primary-color: #3b82f6;
  --secondary-color: #10b981;
  --danger-color: #ef4444;
}
```

## 🔧 トラブルシューティング

- 接続できない場合:
  1) backend が起動しているか 2) CORS 設定（`household_mcp/web/http_server.py`） 3) ブラウザコンソールのエラー を確認
- データが表示されない場合:
  1) `data/` にCSVが存在するか 2) `/api/available-months` のレスポンス を確認

## メモ

- 本フォルダは旧 `webapp/` から移設されました。
- ビルド不要。CDN/生JSで動作します。
