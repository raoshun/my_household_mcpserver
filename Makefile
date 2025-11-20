# Makefile for Household MCP Server

.PHONY: help install install-dev setup-pre-commit clean test lint format check-all
.DEFAULT_GOAL := help

# 変数定義
PYTHON := python3
PIP := pip
PYTEST := uv run pytest
PRE_COMMIT := pre-commit

# Learning & Towncrier parameters (overridable via make VAR=value)
CONCEPT ?= CSVリーダー
TARGET_CONCEPT ?= SQLiteの複雑なJOINクエリ
TDD_PHASE ?= red
CHANGE_DESC ?= 新機能を追加

help: ## このヘルプメッセージを表示
	@echo "利用可能なコマンド:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

install: ## 本番用依存関係をインストール（backend/uv）
	cd backend && uv install

install-dev: ## 開発用依存関係をインストール（backend/uv, dev）
	cd backend && uv sync --dev

setup-pre-commit: ## pre-commitフックをセットアップ
	$(PRE_COMMIT) install
	$(PRE_COMMIT) install --hook-type commit-msg
	$(PRE_COMMIT) autoupdate

clean: ## キャッシュファイルとビルド成果物を削除
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf build/ dist/ htmlcov/ .coverage

test: ## テストを実行
	cd backend && $(PYTEST) -v

test-cov: ## カバレッジ付きでテストを実行
	cd backend && $(PYTEST) --cov=src/household_mcp --cov-report=html --cov-report=term

test-unit: ## unit テストのみを実行（integration マーカーの付いたテストを除外）
	cd backend && $(PYTEST) -m "not integration and not slow"

test-integration: ## integration テストのみを実行（DB/CSV/HTTPなどの重いテスト）
	cd backend && $(PYTEST) -m integration

lint: ## リンターを実行（ruff）
	cd backend && uv run ruff check .

lint-pre-commit: ## リンターを実行（pre-commit 全体）
	$(PRE_COMMIT) run --all-files

lint-ruff: ## リンターを実行（ruff）
	cd backend && uv run ruff check .

format: ## コードフォーマットを実行（ruff）
	cd backend && uv run ruff format .

format-ruff: ## コードフォーマットを実行（ruff）
	cd backend && uv run ruff format .

mypy: ## 型チェックを実行
	cd backend && uv run mypy src/

bandit: ## セキュリティチェックを実行
	cd backend && uv run bandit -r src/ -f json -o bandit-report.json

check-all: ## すべてのチェックを実行
	make lint
	make mypy
	make test-cov
	make bandit

init-secrets: ## detect-secretsのベースラインを初期化
	detect-secrets scan --baseline .secrets.baseline

check-secrets: ## シークレットをチェック
	detect-secrets scan --baseline .secrets.baseline

# Learning Support (separated from VS Code tasks)
learn-check: ## 学習: 理解度チェック（CONCEPT=...）
	python .learning_support/understanding_checker.py "$(CONCEPT)"

learn-path: ## 学習: 学習パス生成（TARGET_CONCEPT=...）
	python .learning_support/learning_path_generator.py "$(TARGET_CONCEPT)"

learn-tdd: ## 学習: TDD記録（TDD_PHASE=red|green|refactor, CONCEPT=...）
	python .learning_support/tdd_tracker.py "$(TDD_PHASE)" "$(CONCEPT)"

learn-review: ## 学習: 復習スケジュール確認
	python .learning_support/review_scheduler.py --check

learn-full: ## 学習: フルチェック実行
	python .learning_support/full_learning_check.py

# Towncrier helpers (separated from VS Code tasks)
tc-feature: ## Towncrier: 機能フラグメント作成（CHANGE_DESC=...）
	python .learning_support/changelog_helper.py create feature "$(CHANGE_DESC)"

tc-bugfix: ## Towncrier: バグ修正フラグメント作成（CHANGE_DESC=...）
	python .learning_support/changelog_helper.py create bugfix "$(CHANGE_DESC)"

tc-draft: ## Towncrier: 変更履歴ドラフト生成
	towncrier --draft

run-dev: ## 開発サーバーを起動（backend/）
	cd backend && uv run uvicorn household_mcp.server:app --reload --host 0.0.0.0 --port 8000

run-http-api: ## HTTP API サーバーを起動（backend/）
	cd backend && uv run python -m uvicorn household_mcp.web.http_server:create_http_app --factory --reload --host 0.0.0.0 --port 8000

run-http-frontend: ## フロントエンド HTTP サーバーを起動（frontend/）
	cd frontend && python3 -m http.server 8080

run-webapp: ## フルスタック（API + フロントエンド）を起動
	@echo "API サーバー（ポート8000）とフロントエンド（ポート8080）を起動しています..."
	@make -j2 run-http-api run-http-frontend

stop-webapp: ## フルスタックを停止（ポート8000, 8080）
	@echo "=== ポート8080（フロントエンド）を停止 ===" && \
	lsof -i :8080 | grep -v COMMAND | awk '{print $$2}' | xargs -r kill -15 && sleep 2 && \
	echo "=== ポート8000（バックエンド）を停止 ===" && \
	lsof -i :8000 | grep -v COMMAND | awk '{print $$2}' | xargs -r kill -15 && sleep 2 && \
	echo "=== 停止確認 ===" && \
	(lsof -i :8000 2>/dev/null && echo "⚠️  ポート8000: まだ起動中" || echo "✅ ポート8000: 停止完了") && \
	(lsof -i :8080 2>/dev/null && echo "⚠️  ポート8080: まだ起動中" || echo "✅ ポート8080: 停止完了")

# Docker コマンド
docker-build: ## Docker イメージをビルド
	docker compose build

docker-up: ## Docker フルスタックを起動（フォアグラウンド）
	docker compose up

docker-up-detach: ## Docker フルスタックを起動（バックグラウンド）
	docker compose up -d

docker-down: ## Docker フルスタックを停止
	docker compose down

docker-logs: ## Docker ログを表示
	docker compose logs -f

docs: ## ドキュメントを生成
	cd docs && make html

setup: ## 初回セットアップ（仮想環境作成後に実行）
	make install-dev
	make setup-pre-commit
	make init-secrets
	@echo "セットアップが完了しました！"
	@echo "次のコマンドでテストを実行できます: make test"

# CI用のコマンド
ci-install: ## CI環境用のインストール
	$(PIP) install -e ".[dev]"

ci-test: ## CI環境用のテスト実行
	$(PYTEST) --cov=src/household_mcp --cov-report=xml --junitxml=pytest.xml

ci-lint: ## CI環境用のリント実行（ruff + mypy + bandit）
	cd backend && uv run ruff format --check .
	cd backend && uv run ruff check .
	mypy src/
	bandit -r src/
