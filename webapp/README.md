# 家計簿分析Webアプリ

HTTPサーバと通信して家計簿をインタラクティブに操作できるWebアプリケーションです。

## 📋 概要

このWebアプリは、Household Budget MCP Serverと通信し、家計簿データの可視化と分析を行います。

### 主な機能

- ✅ 月次データの表示と分析
- ✅ インタラクティブなグラフ表示（円グラフ、棒グラフ、折れ線グラフ）
- ✅ データテーブルの表示と検索・フィルタリング
- ✅ 概要統計（総支出、取引件数、平均支出、最大支出）
- ✅ レスポンシブデザイン（モバイル対応）

## 🏗️ アーキテクチャ

```
webapp/
├── index.html          # メインHTMLファイル
├── css/
│   └── style.css      # スタイルシート
├── js/
│   ├── api.js         # API通信クライアント
│   ├── chart.js       # チャート管理
│   └── main.js        # メインアプリケーションロジック
└── README.md          # このファイル
```

### 技術スタック

- **フロントエンド**: Vanilla JavaScript (ES6+)
- **UI**: HTML5 + CSS3（カスタムスタイル）
- **チャートライブラリ**: Chart.js v4.4.0
- **バックエンドAPI**: FastAPI (Household Budget MCP Server)

## 🚀 使い方

### 1. サーバーの起動

まず、バックエンドサーバーを起動します：

```bash
# プロジェクトルートから
cd /home/shun-h/my_household_mcpserver

# サーバー起動（開発モード）
uv run uvicorn household_mcp.server:app --reload --host 0.0.0.0 --port 8000

# または、タスクを使用
uv run run_task "Start Dev Server" /home/shun-h/my_household_mcpserver
```

サーバーが起動すると、以下のエンドポイントが利用可能になります：
- `http://localhost:8000` - APIサーバー
- `http://localhost:8000/docs` - API仕様（Swagger UI）

### 2. Webアプリの起動

Webアプリは静的ファイルなので、シンプルなHTTPサーバーで配信できます：

#### 方法1: Pythonの内蔵HTTPサーバー

```bash
# webappディレクトリに移動
cd webapp

# HTTPサーバー起動
python -m http.server 8080
```

ブラウザで `http://localhost:8080` を開きます。

#### 方法2: VS Code Live Server拡張機能

1. VS Codeで `webapp/index.html` を開く
2. 右クリック → "Open with Live Server"

#### 方法3: 直接ファイルを開く

CORS設定が有効な場合、`webapp/index.html` をブラウザで直接開くこともできます。

### 3. アプリの操作

1. **期間選択**: 年と月を選択
2. **グラフ種類選択**: 円グラフ、棒グラフ、折れ線グラフから選択
3. **データ読み込み**: 「データ読み込み」ボタンをクリック
4. **データ表示**: グラフ、統計、テーブルが更新されます
5. **検索・フィルタ**: テーブル上部の検索ボックスやカテゴリフィルタを使用

## 🔌 API仕様

### エンドポイント

#### `GET /api/available-months`
利用可能な年月の一覧を取得

**レスポンス:**
```json
{
  "success": true,
  "months": [
    {"year": 2025, "month": 1},
    {"year": 2025, "month": 2}
  ]
}
```

#### `GET /api/monthly`
月次データを取得

**パラメータ:**
- `year` (int): 年
- `month` (int): 月（1-12）
- `output_format` (str): 出力形式（"json" または "image"）
- `graph_type` (str): グラフタイプ（"pie", "bar", "line", "area"）
- `image_size` (str): 画像サイズ（例: "800x600"）

**レスポンス:**
```json
{
  "success": true,
  "year": 2025,
  "month": 1,
  "data": [
    {
      "日付": "2025-01-01",
      "内容": "食費",
      "大項目": "食費",
      "金額": -5000
    }
  ],
  "count": 100
}
```

#### `GET /api/category-hierarchy`
カテゴリ階層を取得

**パラメータ:**
- `year` (int): 年（デフォルト: 2025）
- `month` (int): 月（デフォルト: 1）

#### `GET /health`
ヘルスチェック

## 🎨 カスタマイズ

### API URLの変更

`webapp/js/api.js` の `API_BASE_URL` を変更します：

```javascript
const API_BASE_URL = 'http://your-server:8000';
```

### スタイルのカスタマイズ

`webapp/css/style.css` の CSS変数を変更することで、カラーテーマをカスタマイズできます：

```css
:root {
    --primary-color: #3b82f6;
    --secondary-color: #10b981;
    --danger-color: #ef4444;
    /* ... */
}
```

## 🔧 トラブルシューティング

### サーバーに接続できない

1. バックエンドサーバーが起動しているか確認
2. CORS設定を確認（`http_server.py`の`allowed_origins`）
3. ブラウザのコンソールでエラーを確認

### データが表示されない

1. データファイル（CSV）が `data/` ディレクトリに存在するか確認
2. APIエンドポイント `/api/available-months` でデータの有無を確認
3. ブラウザのコンソールでAPIエラーを確認

### CORSエラー

サーバー側でCORSを有効にする必要があります。`src/household_mcp/web/http_server.py` で：

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # または特定のオリジン
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)
```

## 📝 今後の拡張予定

- [ ] カテゴリ別トレンド分析
- [ ] 予算管理機能
- [ ] データエクスポート（CSV, PDF）
- [ ] ダッシュボードのカスタマイズ
- [ ] 複数月の比較
- [ ] 詳細な統計分析

## 🤝 貢献

バグ報告や機能リクエストは、GitHubのIssueで受け付けています。

## 📄 ライセンス

このプロジェクトは、親プロジェクト（Household Budget MCP Server）と同じライセンスです。
