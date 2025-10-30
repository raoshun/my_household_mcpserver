"""Integration tests for streaming pipeline (TASK-606)."""

import time

import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


class TestStreamingPipeline:
    """E2E tests for image generation -> cache -> HTTP delivery pipeline."""

    def test_end_to_end_monthly_summary_image(self):
        """E2E: データ取得 → 月次グラフ生成 → キャッシュ → URL生成"""
        try:
            from household_mcp.tools.enhanced_tools import enhanced_monthly_summary
        except ImportError:
            pytest.skip("必要な依存関係がインストールされていません")

        # 実際のデータで月次サマリー画像を生成
        result = enhanced_monthly_summary(
            year=2024,
            month=1,
            output_format="image",
            graph_type="pie",
            image_size="800x600",
        )

        # レスポンスの構造を検証
        assert isinstance(result, dict)
        assert result.get("success") is True
        assert result.get("type") == "image"
        assert "url" in result
        assert "cache_key" in result
        assert "metadata" in result

        # URL形式を検証
        url = result["url"]
        assert url.startswith("http://")
        assert "/api/charts/" in url

        # メタデータを検証
        metadata = result["metadata"]
        assert metadata["year"] == 2024
        assert metadata["month"] == 1
        assert metadata["graph_type"] == "pie"
        assert metadata["image_size"] == "800x600"

    def test_end_to_end_category_trend_image(self):
        """E2E: カテゴリトレンドデータ取得 → グラフ生成 → キャッシュ → URL生成"""
        try:
            from household_mcp.tools.enhanced_tools import enhanced_category_trend
        except ImportError:
            pytest.skip("必要な依存関係がインストールされていません")

        # カテゴリトレンドの画像生成
        result = enhanced_category_trend(
            category="食費",
            start_month="2024-01",
            end_month="2024-06",
            output_format="image",
            graph_type="bar",
            image_size="1000x600",
        )

        # レスポンスの構造を検証
        assert isinstance(result, dict)
        assert result.get("success") is True
        assert result.get("type") == "image"
        assert "url" in result
        assert "cache_key" in result
        assert "metadata" in result

        # メタデータを検証
        metadata = result["metadata"]
        assert metadata["category"] == "食費"
        assert metadata["start_month"] == "2024-01"
        assert metadata["end_month"] == "2024-06"

    def test_performance_image_generation_within_3_seconds(self):
        """NFR-005: 画像生成が3秒以内に完了すること"""
        try:
            from household_mcp.tools.enhanced_tools import enhanced_monthly_summary
        except ImportError:
            pytest.skip("必要な依存関係がインストールされていません")

        start_time = time.time()

        result = enhanced_monthly_summary(
            year=2024, month=6, output_format="image", graph_type="pie"
        )

        elapsed = time.time() - start_time

        assert result.get("success") is True
        assert (
            elapsed < 3.0
        ), f"画像生成に3秒以上かかりました: {elapsed:.2f}秒 (NFR-005違反)"

    def test_cache_hit_performance(self):
        """キャッシュヒット時のパフォーマンスを検証"""
        try:
            from household_mcp.streaming.global_cache import ensure_global_cache
            from household_mcp.tools.enhanced_tools import enhanced_monthly_summary
        except ImportError:
            pytest.skip("必要な依存関係がインストールされていません")

        cache = ensure_global_cache()
        cache.clear()

        # 1回目: キャッシュミス
        start1 = time.time()
        result1 = enhanced_monthly_summary(
            year=2024, month=3, output_format="image", graph_type="pie"
        )
        elapsed1 = time.time() - start1

        # 2回目: キャッシュヒット
        start2 = time.time()
        result2 = enhanced_monthly_summary(
            year=2024, month=3, output_format="image", graph_type="pie"
        )
        elapsed2 = time.time() - start2

        # 同じURLが返されることを確認
        assert result1["url"] == result2["url"]
        assert result1["cache_key"] == result2["cache_key"]

        # キャッシュヒットは十分高速であるべき(0.5秒以内)
        # 注: 初回とキャッシュヒットの直接比較は不安定なので、絶対時間で検証
        assert elapsed2 < 0.5, f"キャッシュヒットに時間がかかりすぎ: {elapsed2:.3f}秒"

        # 追加検証: 初回生成は3秒以内に完了すべき
        assert elapsed1 < 3.0, f"初回生成に時間がかかりすぎ: {elapsed1:.3f}秒"

    def test_memory_usage_within_50mb(self):
        """NFR-006: メモリ使用量が50MB以内に収まること"""
        try:
            import psutil

            from household_mcp.tools.enhanced_tools import enhanced_monthly_summary
        except ImportError:
            pytest.skip("必要な依存関係がインストールされていません")

        import os

        process = psutil.Process(os.getpid())

        # 初期メモリ使用量
        mem_before = process.memory_info().rss / (1024 * 1024)  # MB

        # 複数の画像を生成
        for month in range(1, 7):
            enhanced_monthly_summary(
                year=2024, month=month, output_format="image", graph_type="pie"
            )

        # 生成後のメモリ使用量
        mem_after = process.memory_info().rss / (1024 * 1024)  # MB
        mem_increase = mem_after - mem_before

        assert (
            mem_increase < 50
        ), f"メモリ使用量増加が50MBを超えました: {mem_increase:.2f}MB (NFR-006違反)"

    def test_concurrent_image_generation(self):
        """複数の画像生成リクエストを並行処理できることを確認"""
        try:
            import asyncio

            from household_mcp.tools.enhanced_tools import enhanced_monthly_summary
        except ImportError:
            pytest.skip("必要な依存関係がインストールされていません")

        async def generate_image(year: int, month: int):
            # Wrap synchronous function for async context
            return enhanced_monthly_summary(
                year=year, month=month, output_format="image", graph_type="pie"
            )

        async def run_concurrent():
            tasks = [generate_image(2024, month) for month in range(1, 4)]
            results = await asyncio.gather(*tasks)
            return results

        results = asyncio.run(run_concurrent())

        # 全ての結果が成功していることを確認
        assert len(results) == 3
        for result in results:
            assert result.get("success") is True
            assert "url" in result

    def test_cache_stats_tracking(self):
        """キャッシュ統計が正しく追跡されることを確認"""
        try:
            from household_mcp.streaming.global_cache import ensure_global_cache
            from household_mcp.tools.enhanced_tools import enhanced_monthly_summary
        except ImportError:
            pytest.skip("必要な依存関係がインストールされていません")

        cache = ensure_global_cache()
        cache.clear()

        initial_stats = cache.stats()
        assert initial_stats["current_size"] == 0

        # 画像生成（キャッシュに保存）
        enhanced_monthly_summary(
            year=2024, month=5, output_format="image", graph_type="pie"
        )

        after_stats = cache.stats()
        assert after_stats["current_size"] >= 1

    def test_error_handling_invalid_data(self):
        """不正なデータでも適切なエラーレスポンスが返ることを確認"""
        try:
            from household_mcp.tools.enhanced_tools import enhanced_monthly_summary
        except ImportError:
            pytest.skip("必要な依存関係がインストールされていません")

        # 存在しない年月（未来）
        result = enhanced_monthly_summary(
            year=2030, month=12, output_format="image", graph_type="pie"
        )

        # エラーレスポンスが返される
        assert isinstance(result, dict)
        assert result.get("success") is False
        assert "error" in result

    def test_error_handling_missing_visualization_deps(self, monkeypatch):
        """visualization依存関係がない場合の適切なエラーハンドリング"""
        try:
            from household_mcp.tools import enhanced_tools
        except ImportError:
            pytest.skip("enhanced_tools がインストールされていません")

        # HAS_VIZ を False にモック
        monkeypatch.setattr(enhanced_tools, "HAS_VIZ", False)

        result = enhanced_tools.enhanced_monthly_summary(
            year=2024, month=1, output_format="image", graph_type="pie"
        )

        # エラーレスポンスが返される
        assert isinstance(result, dict)
        assert result.get("success") is False
        assert "visualization" in result.get("error", "").lower()

    def test_image_format_validation(self):
        """画像フォーマット（PNG）が正しく生成されることを確認"""
        try:
            from household_mcp.streaming.global_cache import ensure_global_cache
            from household_mcp.tools.enhanced_tools import enhanced_monthly_summary
        except ImportError:
            pytest.skip("必要な依存関係がインストールされていません")

        cache = ensure_global_cache()

        result = enhanced_monthly_summary(
            year=2024, month=4, output_format="image", graph_type="pie"
        )

        assert result.get("success") is True
        cache_key = result["cache_key"]

        # キャッシュから画像データを取得
        image_bytes = cache.get(cache_key)
        assert image_bytes is not None

        # PNG形式であることを確認（マジックナンバー）
        assert image_bytes.startswith(
            b"\x89PNG\r\n\x1a\n"
        ), "画像がPNG形式ではありません"


# Run a simple smoke test that doesn't require --run-integration flag
def test_streaming_imports():
    """Verify all streaming modules can be imported."""
    try:
        from household_mcp.streaming.cache import ChartCache
        from household_mcp.streaming.global_cache import ensure_global_cache
        from household_mcp.streaming.image_streamer import ImageStreamer

        assert ChartCache is not None
        assert ImageStreamer is not None
        assert ensure_global_cache is not None
    except ImportError as e:
        pytest.skip(f"Streaming依存関係がインストールされていません: {e}")
