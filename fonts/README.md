# フォントディレクトリ

このディレクトリには、グラフ生成時に使用する日本語フォントを配置します。

## フォントの入手方法

### Noto Sans CJK (推奨)

Google が提供するオープンソースの日本語フォントです。

1. **ダウンロード**:
   ```bash
   # Debian/Ubuntu の場合
   sudo apt-get install fonts-noto-cjk
   
   # または、直接ダウンロード
   wget https://github.com/googlefonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansCJK-Regular.ttc
   ```

2. **配置**:
   ```bash
   cp /usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc ./fonts/
   # または
   mv NotoSansCJK-Regular.ttc ./fonts/
   ```

### システムフォントの使用

フォントファイルを配置しない場合、ChartGenerator は以下の順序でシステムフォントを自動検出します:

1. `/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf` (Linux)
2. `/System/Library/Fonts/Hiragino Sans GB.ttc` (macOS)
3. `C:/Windows/Fonts/msgothic.ttc` (Windows)

## ライセンス

- **Noto Sans CJK**: SIL Open Font License 1.1
  - https://github.com/googlefonts/noto-cjk

## 使用方法

ChartGenerator は以下の優先順位でフォントをロードします:

1. コンストラクタで明示的に指定されたパス
2. `fonts/` ディレクトリ内のフォントファイル
3. システムフォントの自動検出

```python
from household_mcp.visualization.chart_generator import ChartGenerator

# 明示的にフォントを指定
generator = ChartGenerator(font_path="fonts/NotoSansCJK-Regular.ttc")

# 自動検出を使用
generator = ChartGenerator()
```
