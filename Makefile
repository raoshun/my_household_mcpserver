# Makefile for Household MCP Server

.PHONY: help install install-dev setup-pre-commit clean test lint format check-all
.DEFAULT_GOAL := help

# 変数定義
PYTHON := python3
PIP := pip
PYTEST := uv run pytest
PRE_COMMIT := pre-commit

help: ## このヘルプメッセージを表示
	@echo "利用可能なコマンド:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

install: ## 本番用依存関係をインストール
	$(PIP) install -e .

install-dev: ## 開発用依存関係をインストール
	$(PIP) install -e ".[dev]"
	$(PIP) install -r requirements-dev.txt

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
	$(PYTEST) -v

test-cov: ## カバレッジ付きでテストを実行
	$(PYTEST) --cov=src/household_mcp --cov-report=html --cov-report=term

test-unit: ## unit テストのみを実行（integration マーカーの付いたテストを除外）
	$(PYTEST) -m "not integration and not slow"

test-integration: ## integration テストのみを実行（DB/CSV/HTTPなどの重いテスト）
	$(PYTEST) -m integration

lint: ## リンターを実行
	$(PRE_COMMIT) run --all-files

format: ## コードフォーマットを実行
	black src/ tests/
	isort src/ tests/

mypy: ## 型チェックを実行
	mypy src/

bandit: ## セキュリティチェックを実行
	bandit -r src/ -f json -o bandit-report.json

check-all: ## すべてのチェックを実行
	make lint
	make mypy
	make test-cov
	make bandit

init-secrets: ## detect-secretsのベースラインを初期化
	detect-secrets scan --baseline .secrets.baseline

check-secrets: ## シークレットをチェック
	detect-secrets scan --baseline .secrets.baseline

run-dev: ## 開発サーバーを起動
	uvicorn src.household_mcp.server:app --reload --host 0.0.0.0 --port 8000

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

ci-lint: ## CI環境用のリント実行
	black --check src/ tests/
	isort --check-only src/ tests/
	flake8 src/ tests/
	mypy src/
	bandit -r src/
