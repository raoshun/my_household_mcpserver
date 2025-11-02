# Deployment Guide - Household Budget MCP Server

本ガイドでは、Household Budget MCP Serverをデプロイする方法を説明します。

## 目次

1. [前提条件](#前提条件)
2. [開発環境のセットアップ](#開発環境のセットアップ)
3. [本番環境のデプロイ](#本番環境のデプロイ)
4. [環境変数設定](#環境変数設定)
5. [トラブルシューティング](#トラブルシューティング)

---

## 前提条件

### 必須ソフトウェア

- **Docker**: バージョン 20.10 以上
- **Docker Compose**: バージョン 2.0 以上

### システム要件

- **OS**: Linux (Ubuntu 20.04+, Debian 11+, RHEL 8+ など)
- **メモリ**: 最低 2GB (推奨 4GB+)
- **ディスク**: 最低 5GB の空き容量
- **CPU**: 2コア以上推奨

### インストール確認

```bash
# Docker のバージョン確認
docker --version

# Docker Compose のバージョン確認
docker compose version
```

---

## 開発環境のセットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/yourusername/my_household_mcpserver.git
cd my_household_mcpserver
```

### 2. 環境変数の設定

```bash
# .env.example から .env をコピー
cp .env.example .env

# 必要に応じて .env を編集
nano .env
```

### 3. データディレクトリの準備

```bash
# data/ ディレクトリが存在することを確認
ls -la data/

# CSVファイルを配置
# 例: 収入・支出詳細_YYYY-MM-01_YYYY-MM-31.csv
```

### 4. 開発環境の起動

```bash
# スクリプトに実行権限を付与
chmod +x scripts/*.sh

# 開発環境を起動
./scripts/start-dev.sh
```

### 5. 動作確認

開発環境が起動したら、以下のURLにアクセスして動作を確認します：

- **フロントエンド**: <http://localhost:8080>
- **バックエンド API**: <http://localhost:8000>
- **API ドキュメント**: <http://localhost:8000/docs>

### 6. ログの確認

```bash
# すべてのサービスのログを表示
docker compose logs -f

# 特定のサービスのログのみ表示
docker compose logs -f backend
docker compose logs -f frontend
```

### 7. 開発環境の停止

```bash
./scripts/stop.sh
```

---

## 本番環境のデプロイ

### 1. 環境変数の設定（本番用）

```bash
# .env を本番設定で編集
nano .env
```

**本番環境での推奨設定**:

```env
# Backend Configuration
BACKEND_PORT=8000
LOG_LEVEL=warning  # info から warning に変更
DATA_DIR=./data

# Frontend Configuration
FRONTEND_PORT=8080

# Nginx Reverse Proxy
NGINX_PORT=80

# Python Configuration
PYTHONUNBUFFERED=1
```

### 2. 本番環境の起動

```bash
# 本番環境を起動（nginx リバースプロキシ含む）
./scripts/start-prod.sh
```

本番環境では以下のサービスが起動します：

- **backend**: Python API サーバー (ポート 8000)
- **frontend**: 静的ファイルサーバー (ポート 8080)
- **nginx**: リバースプロキシ (ポート 80)

### 3. アクセス確認

- **メインURL**: <http://localhost>
- **API ドキュメント**: <http://localhost/api/docs>

### 4. セキュリティ設定

本番環境では以下のセキュリティ対策を実施してください：

#### ファイアウォール設定

```bash
# UFW を使用する場合（Ubuntu）
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

#### HTTPS の設定

本番環境では HTTPS を有効にすることを強く推奨します：

**Let's Encrypt を使用する場合**:

```bash
# Certbot のインストール
sudo apt-get install certbot python3-certbot-nginx

# SSL 証明書の取得
sudo certbot --nginx -d yourdomain.com
```

**nginx 設定の更新**:

`nginx/conf.d/default.conf` に以下を追加：

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # SSL 設定...
}
```

### 5. バックアップ設定

データディレクトリの定期バックアップを設定します：

```bash
# バックアップスクリプトの例
#!/bin/bash
BACKUP_DIR="/backup/household_data"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/data_$DATE.tar.gz data/

# 30日以上前のバックアップを削除
find $BACKUP_DIR -name "data_*.tar.gz" -mtime +30 -delete
```

### 6. 監視とログ管理

```bash
# ログのローテーション設定（/etc/logrotate.d/docker-logs）
/var/lib/docker/containers/*/*.log {
    rotate 7
    daily
    compress
    delaycompress
    missingok
    notifempty
}

# システム監視
docker stats

# ヘルスチェック
curl http://localhost/health
```

---

## 環境変数設定

### 基本設定

| 変数名          | デフォルト値 | 説明                                  |
| --------------- | ------------ | ------------------------------------- |
| `BACKEND_PORT`  | 8000         | バックエンド API のポート             |
| `FRONTEND_PORT` | 8080         | フロントエンドのポート                |
| `NGINX_PORT`    | 80           | nginx のポート                        |
| `LOG_LEVEL`     | info         | ログレベル (debug/info/warning/error) |
| `DATA_DIR`      | ./data       | データディレクトリのパス              |

### 開発環境専用

| 変数名   | デフォルト値 | 説明                 |
| -------- | ------------ | -------------------- |
| `RELOAD` | false        | ホットリロード有効化 |
| `DEBUG`  | false        | デバッグモード有効化 |

---

## Docker Compose コマンドリファレンス

### サービス管理

```bash
# すべてのサービスを起動
docker compose up -d

# 本番環境（nginx 含む）を起動
docker compose --profile production up -d

# サービスを停止
docker compose down

# サービスを再起動
docker compose restart

# 特定のサービスのみ再起動
docker compose restart backend
```

### イメージ管理

```bash
# イメージをビルド
docker compose build

# キャッシュなしでビルド
docker compose build --no-cache

# 不要なイメージを削除
docker system prune -a
```

### ログとデバッグ

```bash
# すべてのログを表示
docker compose logs -f

# 特定のサービスのログ
docker compose logs -f backend

# 最新100行のみ表示
docker compose logs --tail=100
```

### コンテナ内でコマンド実行

```bash
# backend コンテナでシェルを起動
docker compose exec backend bash

# テストを実行
docker compose exec backend pytest

# Python インタラクティブシェル
docker compose exec backend python
```

---

## トラブルシューティング

### 1. サービスが起動しない

**症状**: `docker compose up` が失敗する

**解決策**:

```bash
# ログを確認
docker compose logs

# コンテナの状態を確認
docker compose ps

# ポートが使用中でないか確認
sudo netstat -tulpn | grep LISTEN

# Docker を再起動
sudo systemctl restart docker
```

### 2. ヘルスチェックが失敗する

**症状**: ヘルスチェックが "unhealthy" になる

**解決策**:

```bash
# バックエンドのヘルスチェック
curl -v http://localhost:8000/health

# コンテナ内から確認
docker compose exec backend curl http://localhost:8000/health

# ログを詳細確認
docker compose logs --tail=50 backend
```

### 3. データが読み込めない

**症状**: API がデータを返さない

**解決策**:

```bash
# data/ ディレクトリの権限確認
ls -la data/

# コンテナ内から確認
docker compose exec backend ls -la /app/data/

# ボリュームマウントの確認
docker compose config | grep -A5 volumes
```

### 4. フロントエンドがバックエンドに接続できない

**症状**: API エラーが表示される

**解決策**:

1. **ブラウザの開発者ツールでネットワークタブを確認**
2. **CORS 設定を確認** (`nginx/conf.d/default.conf`)
3. **バックエンドの起動を確認**:

```bash
curl http://localhost:8000/api/available-months
```

### 5. メモリ不足

**症状**: コンテナが OOMKilled される

**解決策**:

```bash
# Docker のメモリ制限を確認
docker stats

# メモリ制限を増やす（docker-compose.yml）
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 2G
```

### 6. SSL 証明書エラー

**症状**: HTTPS 接続がエラーになる

**解決策**:

```bash
# 証明書の有効期限を確認
sudo certbot certificates

# 証明書を更新
sudo certbot renew

# nginx 設定をテスト
docker compose exec nginx nginx -t
```

---

## パフォーマンスチューニング

### 1. Docker リソース制限

```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

### 2. nginx キャッシュ設定

```nginx
# nginx/conf.d/default.conf
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m max_size=100m inactive=60m;

location /api/ {
    proxy_cache api_cache;
    proxy_cache_valid 200 5m;
    proxy_cache_key "$scheme$request_method$host$request_uri";
}
```

### 3. Python アプリケーション最適化

```python
# backend/src/household_mcp/web/http_server.py
# uvicorn の worker 数を調整
uvicorn.run(app, workers=4)
```

---

## アップグレード手順

### 1. バックアップ

```bash
# データのバックアップ
tar -czf backup_$(date +%Y%m%d).tar.gz data/

# 設定のバックアップ
cp .env .env.backup
```

### 2. コードの更新

```bash
# 最新コードを取得
git pull origin main

# イメージを再ビルド
docker compose build --no-cache
```

### 3. サービスの再起動

```bash
# ダウンタイムを最小化するローリングアップデート
docker compose up -d --no-deps --build backend
docker compose up -d --no-deps --build frontend
```

### 4. 動作確認

```bash
# ヘルスチェック
curl http://localhost/health

# ログ確認
docker compose logs --tail=50
```

---

## サポート

問題が解決しない場合は、以下の情報を含めて Issue を作成してください：

- OS とバージョン
- Docker / Docker Compose のバージョン
- エラーメッセージとログ
- `docker compose config` の出力
- 再現手順

GitHub Issue: <https://github.com/yourusername/my_household_mcpserver/issues>
