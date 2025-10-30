# FAQ（よくある質問）

## インストールと環境設定

### Q1: どのPythonバージョンが必要ですか?

**A**: Python 3.12以上が必要です。Python 3.14での動作確認済みです。

```bash
python --version  # 3.12以上であることを確認
```

### Q2: uvとpipのどちらを使うべきですか?

**A**: `uv` の使用を推奨します。高速で依存関係の解決が確実です。

```bash
# uv のインストール
curl -LsSf https://astral.sh/uv/install.sh | sh

# プロジェクトのインストール
uv pip install -e ".[dev,full]"
```

### Q3: 画像生成機能だけ追加したい

**A**: `visualization` オプションをインストールしてください。

```bash
uv pip install -e ".[visualization]"
```

### Q4: HTTPサーバーとして起動したい

**A**: `streaming` または `web` オプションが必要です。

```bash
uv pip install -e ".[streaming]"
python -m src.server --transport streamable-http --port 8000
```

## データと CSV

### Q5: どんな形式のCSVが必要ですか?

**A**: 以下の列が必要です：

- 日付（YYYY-MM-DD形式）
- 金額（円）- 支出は負の値、収入は正の値
- 大項目（カテゴリ）
- 中項目（サブカテゴリ）

**ファイル名形式**: `収入・支出詳細_YYYY-MM-DD_YYYY-MM-DD.csv`

### Q6: CSVファイルはどこに配置しますか?

**A**: プロジェクトルートの `data/` ディレクトリに配置してください。

```bash
my_household_mcpserver/
├── data/
│   ├── 収入・支出詳細_2024-01-01_2024-01-31.csv
│   ├── 収入・支出詳細_2024-02-01_2024-02-29.csv
│   └── ...
```

### Q7: 複数年のデータを扱えますか?

**A**: はい。`data/` ディレクトリ内のすべてのCSVファイルを自動的に読み込みます。

### Q8: データのプライバシーは保護されますか?

**A**: はい。すべての処理はローカルで実行され、外部サーバーにデータは送信されません。

## 画像生成

### Q9: 日本語が文字化けします

**A**: 日本語フォントをインストールしてください。

```bash
# Noto Sans CJK のダウンロード
wget https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansCJKjp-Regular.otf -O fonts/NotoSansCJKjp-Regular.otf

# または、システムフォントのインストール
sudo apt-get install fonts-noto-cjk  # Debian/Ubuntu
```

詳細は `README.md` の「日本語フォント設定」を参照してください。

### Q10: グラフの画像サイズを変更できますか?

**A**: はい。`image_size` パラメータで指定できます。

```json
{
  "tool": "get_monthly_household",
  "arguments": {
    "year": 2024,
    "month": 10,
    "output_format": "image",
    "graph_type": "pie",
    "image_size": "1920x1080"
  }
}
```

推奨サイズ: `800x600`, `1024x768`, `1280x720`, `1920x1080`

### Q11: SVG形式で出力できますか?

**A**: はい。`image_format` パラメータで指定できます。

```json
{
  "arguments": {
    "output_format": "image",
    "image_format": "svg"
  }
}
```

### Q12: 画像が生成されません

**A**: 以下を確認してください：

1. `visualization` オプションがインストールされているか

   ```bash
   python -c "from household_mcp.visualization import ChartGenerator; print('OK')"
   ```

2. HTTPサーバーが起動しているか（`streaming` モード使用時）

   ```bash
   curl http://localhost:8000/health
   ```

3. データが存在する期間を指定しているか

   ```json
   {
     "tool": "data://available_months"
   }
   ```

## トレンド分析

### Q13: カテゴリ名がわかりません

**A**: `find_categories` ツールで検索できます。

```json
{
  "tool": "find_categories",
  "arguments": {
    "pattern": "食"
  }
}
```

### Q14: 前月比がnullになります

**A**: 初月（比較対象がない月）は前月比が計算できません。これは正常な動作です。

```json
{
  "month": "2024-01",
  "amount": -80000,
  "month_over_month": null  // 比較対象なし
}
```

### Q15: 移動平均が表示されません

**A**: 12ヶ月移動平均は12ヶ月分のデータがある場合のみ計算されます。

### Q16: トレンド分析の期間制限はありますか?

**A**: 特に制限はありませんが、CSVファイルに存在する期間内でのみ分析できます。

## パフォーマンス

### Q17: 画像生成が遅い

**A**: 初回生成は3秒程度かかります。2回目以降はキャッシュにより0.5秒以内で返されます。

キャッシュ統計を確認:

```bash
curl http://localhost:8000/api/cache/stats
```

### Q18: キャッシュをクリアしたい

**A**: DELETE リクエストでキャッシュをクリアできます。

```bash
curl -X DELETE http://localhost:8000/api/cache
```

### Q19: メモリ使用量が多い

**A**: 通常は50MB以内です。大量の画像を並行生成する場合は増加する可能性があります。

キャッシュサイズを制限する場合は環境変数で調整できます：

```bash
export CHART_CACHE_MAX_SIZE=50
```

## エラー対処

### Q20: "No data available for the specified period"

**原因**: 指定期間のCSVファイルが存在しない

**対処法**:

```json
{
  "tool": "data://available_months"
}
```

で利用可能な期間を確認してください。

### Q21: "Category not found: ○○"

**原因**: カテゴリ名が正確でない

**対処法**:

```json
{
  "tool": "find_categories",
  "arguments": {
    "pattern": "○○"
  }
}
```

でカテゴリを検索し、正確な名称を使用してください。

### Q22: "Visualization dependencies not installed"

**原因**: 画像生成に必要なパッケージがインストールされていない

**対処法**:

```bash
uv pip install -e ".[visualization]"
```

### Q23: "Cannot identify category and amount columns"

**原因**: DataFrameの列名が期待される形式と異なる

**対処法**: これは内部エラーです。以下をGitHub Issueで報告してください：

- 使用したツール名とパラメータ
- エラーメッセージ全文
- CSVファイルの列名リスト

### Q24: テストが失敗する

**原因**: 依存パッケージや環境設定の問題

**対処法**:

```bash
# 依存関係を再インストール
uv pip install -e ".[dev,full]"

# テスト実行
uv run pytest -v

# 特定のテストのみ実行
uv run pytest tests/unit/test_data_tools.py -v
```

## MCP 統合

### Q25: Claude Desktop で使用できますか?

**A**: はい。`claude_desktop_config.json` に以下を追加してください：

```json
{
  "mcpServers": {
    "household": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/my_household_mcpserver"
    }
  }
}
```

### Q26: HTTPサーバーモードとstdioモードの違いは?

**A**:

- **stdio モード**: MCP標準。Claude Desktop等と統合
- **HTTP モード**: ブラウザから画像アクセス可能。デバッグに便利

両方を同時に使用することはできません。

### Q27: 他のLLMクライアントで使用できますか?

**A**: MCP プロトコルに対応しているクライアントであれば使用可能です：

- Claude Desktop（Anthropic）
- Continue（VS Code拡張）
- MCPクライアント対応の他のツール

## 開発とカスタマイズ

### Q28: 新しいカテゴリを追加したい

**A**: CSVファイルに新しいカテゴリ名を追加するだけで自動的に認識されます。

### Q29: グラフの色を変更したい

**A**: `src/household_mcp/visualization/chart_generator.py` の `_get_colors()` メソッドをカスタマイズしてください。

### Q30: 独自の分析ツールを追加したい

**A**: 以下の手順で追加できます：

1. `src/household_mcp/tools/` に新しいツールモジュールを作成
2. `src/household_mcp/server.py` にツール定義を追加
3. テストを `tests/unit/` に追加

詳細は `design.md` を参照してください。

## トラブルシューティング全般

### Q31: ログを確認したい

**A**: 標準エラー出力にログが出力されます。

```bash
# ログをファイルに保存
python -m src.server 2> server.log

# リアルタイムで確認
python -m src.server 2>&1 | tee server.log
```

### Q32: デバッグモードで実行したい

**A**: 環境変数 `DEBUG=1` を設定してください。

```bash
DEBUG=1 python -m src.server
```

### Q33: バージョン情報を確認したい

**A**: `pyproject.toml` または以下のコマンドで確認できます：

```bash
python -c "import household_mcp; print(household_mcp.__version__)"
```

### Q34: アップデート方法は?

**A**: git pull して再インストールしてください。

```bash
git pull origin main
uv pip install -e ".[dev,full]"
```

### Q35: 問題が解決しない

**A**: 以下の情報を添えて GitHub Issue を作成してください：

- エラーメッセージ全文
- 使用しているコマンドまたはツール呼び出し
- Python バージョン（`python --version`）
- インストール方法（uv/pip、オプション機能）
- OS とバージョン

## パフォーマンスチューニング

### Q36: キャッシュサイズを調整したい

**A**: 環境変数で設定できます。

```bash
export CHART_CACHE_MAX_SIZE=200  # デフォルト: 100
export CHART_CACHE_TTL=1200      # デフォルト: 600秒
```

### Q37: 並行処理数を増やしたい

**A**: HTTPサーバーのワーカー数を調整してください。

```bash
uvicorn household_mcp.http_server:app --workers 4
```

### Q38: メモリ使用量を削減したい

**A**: キャッシュサイズを減らすか、画像サイズを小さくしてください。

```bash
export CHART_CACHE_MAX_SIZE=25
```

```json
{
  "arguments": {
    "image_size": "640x480"  // 小さいサイズを指定
  }
}
```

## セキュリティ

### Q39: 本番環境で使用できますか?

**A**: ローカル実行を前提としています。公開サーバーでの使用は推奨しません。

### Q40: 認証機能はありますか?

**A**: 現在は実装されていません。`auth` オプションは将来の拡張用です。

## 関連リソース

- [README.md](../README.md) - インストールと概要
- [usage.md](./usage.md) - 詳細な使用方法
- [examples.md](./examples.md) - サンプル会話例
- [api.md](./api.md) - APIリファレンス
- [design.md](../design.md) - 技術設計
