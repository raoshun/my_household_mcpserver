# エラー予防テストスイート

このドキュメントは、今回発生したエラーを予防するために追加されたテストスイートについて説明します。

## 今回発生したエラー

1. **404 エラー**: フロントエンドから `/api/tools` が見つからない
2. **500 エラー**: `Database manager not initialized`
3. **ハードコード問題**: ポート `8001` がハードコードされていた
4. **イメージビルド問題**: 古いコードでビルドされていた
5. **デフォルトポート不一致**: Docker (8000) と開発環境 (8001) のポート不一致

## 追加されたテスト

### 1. バックエンド統合テスト (`backend/tests/integration/test_http_server_endpoints.py`)

#### 目的

HTTP サーバーのエンドポイント可用性と Database manager 初期化を検証

#### テスト項目

- ✅ `/api/tools` エンドポイントが存在し、200 OK を返す
- ✅ `/api/tools` が正しいツール定義を返す
- ✅ すべての必須 MCP ツールが利用可能
- ✅ `/api/duplicates/candidates` エンドポイントが利用可能
- ✅ Database manager が正しく初期化されている
- ✅ CORS ヘッダーが正しく設定されている
- ✅ OpenAPI ドキュメントが利用可能

#### 実行方法

```bash
cd backend
uv run pytest tests/integration/test_http_server_endpoints.py -v
```

### 2. フロントエンド設定テスト (`frontend/tests/config.test.js`)

#### 目的

AppConfig クラスの初期化、API ベース URL 検出、環境別設定を検証

#### テスト項目

- ✅ AppConfig の DEFAULT_API_PORT が 8000 に設定されている
- ✅ API ベース URL が正しいプロトコル・ホスト・ポートを含む
- ✅ localStorage への設定保存と復元が正常に機能
- ✅ URL パラメータ (`?apiBase=...`) がサポートされている
- ✅ 設定優先順位が正しい（localStorage > URL param > auto-detect）
- ✅ Docker (port 8000) と開発環境 (port 8001) 両対応
- ✅ 無効な URL が安全に処理される

#### 実行方法

```bash
cd frontend
npm test config.test.js
# または Jest が必要な場合:
npx jest tests/config.test.js
```

### 3. Docker 統合テスト (`scripts/integration_test.sh`)

#### 目的

Docker Compose で起動したアプリケーション全体の動作を検証

#### テスト項目

- ✅ Docker イメージが正常にビルドされる
- ✅ Docker Compose でコンテナが起動する
- ✅ バックエンドコンテナがヘルスチェック (health: starting) を通過
- ✅ フロントエンドコンテナがヘルスチェックを通過
- ✅ `/api/tools` エンドポイントが 200 OK を返す
- ✅ `/api/duplicates/candidates` エンドポイントが 200 OK を返す
- ✅ フロントエンド index.html が正常に提供される
- ✅ フロントエンド mcp-tools.html が正常に提供される
- ✅ config.js が正常にデプロイされている
- ✅ DEFAULT_API_PORT が 8000 に設定されている
- ✅ OpenAPI ドキュメントが利用可能
- ✅ CORS ヘッダーが正しく設定されている

#### 実行方法

```bash
cd /home/shun-h/my_household_mcpserver
./scripts/integration_test.sh
```

## テスト実行結果の例

```
=== Docker Compose Integration Tests ===

[TEST 1] Checking docker-compose availability...
✓ PASSED

[TEST 2] Checking docker-compose.yml...
✓ PASSED

...

[TEST 15] Testing CORS headers...
✓ PASSED

=== All Tests Passed! ===
```

## エラー予防効果

これらのテストにより、以下のエラーを事前に検出できます：

### 1. 404 エラーの予防

- **テスト 8, 9**: `/api/tools` と `/api/duplicates/candidates` エンドポイントの可用性を確認
- **テスト 13**: デフォルトポート設定の正確性を確認

### 2. 500 エラーの予防

- **テスト 9**: Database manager 初期化状態を確認
- **バックエンド統合テスト**: Database manager 初期化テスト

### 3. ハードコード問題の予防

- **テスト 12, 13**: config.js が正しくデプロイされ、DEFAULT_API_PORT が 8000 に設定されていることを確認
- **フロントエンド設定テスト**: 環境別設定の自動検出機能を検証

### 4. イメージビルド問題の予防

- **テスト 4**: Docker イメージが正常にビルドされることを確認
- **テスト 5**: Docker Compose がコンテナを正常に起動できることを確認

### 5. デフォルトポート不一致の予防

- **テスト 13**: DEFAULT_API_PORT が Docker 環境用に 8000 に設定されていることを確認
- **フロントエンド設定テスト**: 環境別ポート設定のテスト

## CI/CD パイプライン統合

これらのテストは以下のタイミングで実行することを推奨します：

### コミット前

```bash
# フロントエンド設定テスト
cd frontend
npm test config.test.js

# バックエンド統合テスト
cd ../backend
uv run pytest tests/integration/test_http_server_endpoints.py
```

### Docker ビルド後

```bash
# Docker 統合テスト
cd /home/shun-h/my_household_mcpserver
./scripts/integration_test.sh
```

### デプロイ前

- GitHub Actions で上記すべてのテストを実行
- 本番環境へのデプロイ前にパスを確認

## 今後の改善提案

1. **自動化**: GitHub Actions で各コミット時に自動実行
2. **E2E テスト**: Playwright または Selenium でブラウザテストを追加
3. **パフォーマンステスト**: API レスポンスタイムを監視
4. **セキュリティテスト**: CORS、認証、入力検証を検証
5. **ロードテスト**: 複数同時接続でのエンドポイント安定性を確認
