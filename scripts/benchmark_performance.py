#!/usr/bin/env python3
"""Performance benchmark script for TASK-607.

Tests:
- NFR-005: Image generation within 3 seconds
- NFR-006: Memory usage within 50MB
- Transfer speed > 1MB/s
- Concurrent requests (5 simultaneous)
"""
import asyncio
import io
import sys
import time
from pathlib import Path

import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from household_mcp.streaming.image_streamer import ImageStreamer  # noqa: E402
from household_mcp.visualization.chart_generator import (  # noqa: E402
    ChartGenerator,
)

try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("Warning: psutil not installed. Memory profiling will be skipped.")


def measure_memory():
    """Measure current process memory usage in MB."""
    if not HAS_PSUTIL:
        return None
    process = psutil.Process()
    mem_info = process.memory_info()
    return mem_info.rss / (1024 * 1024)  # Convert to MB


def benchmark_image_generation():
    """Benchmark image generation performance (NFR-005)."""
    print("\n=== Image Generation Performance (NFR-005) ===")
    print("Target: < 3 seconds per image\n")
    
    # Create test data for monthly pie chart
    monthly_data = pd.DataFrame({
        "category": [f"カテゴリ{i}" for i in range(20)],
        "amount": [10000 + i * 1000 for i in range(20)]
    })
    
    # Create test data for trend line chart
    trend_data = pd.DataFrame({
        "month": [f"2024-{i:02d}" for i in range(1, 13)],
        "amount": [50000 + i * 5000 for i in range(12)]
    })
    
    # Create test data for comparison bar chart
    comparison_data = pd.DataFrame({
        "category": ["食費", "交通費", "娯楽費", "光熱費", "通信費"],
        "amount": [50000, 20000, 15000, 12000, 8000]
    })
    
    generator = ChartGenerator()
    
    # Test each chart type
    tests = [
        ("pie", lambda: generator.create_monthly_pie_chart(monthly_data, "テスト円グラフ")),
        ("line", lambda: generator.create_category_trend_line(trend_data, "食費", "テスト折れ線グラフ")),
        ("bar", lambda: generator.create_comparison_bar_chart(comparison_data, "テスト棒グラフ"))
    ]
    
    for chart_type, chart_func in tests:
        mem_before = measure_memory()
        start_time = time.time()
        
        buf = chart_func()
        
        elapsed = time.time() - start_time
        mem_after = measure_memory()
        size_kb = buf.getbuffer().nbytes / 1024
        
        status = "✓ PASS" if elapsed < 3.0 else "✗ FAIL"
        print(f"{chart_type.upper():6} | {elapsed:.3f}s | {size_kb:.1f}KB | {status}")
        
        if mem_before and mem_after:
            mem_delta = mem_after - mem_before
            print(f"       | Memory: {mem_before:.1f}MB → {mem_after:.1f}MB (Δ{mem_delta:+.1f}MB)")


def benchmark_memory_usage():
    """Benchmark memory usage during image generation (NFR-006)."""
    print("\n=== Memory Usage Benchmark (NFR-006) ===")
    print("Target: < 50MB for image generation\n")
    
    if not HAS_PSUTIL:
        print("Skipped: psutil not installed")
        return
    
    # Large dataset (100 categories)
    data = pd.DataFrame({
        "category": [f"カテゴリ{i:03d}" for i in range(100)],
        "amount": [5000 + i * 100 for i in range(100)]
    })
    
    generator = ChartGenerator()
    
    # Force garbage collection
    import gc

    gc.collect()
    
    mem_baseline = measure_memory()
    print(f"Baseline memory: {mem_baseline:.2f}MB")
    
    # Generate chart
    start_time = time.time()
    buf = generator.create_monthly_pie_chart(data, "大規模データセット")
    elapsed = time.time() - start_time
    
    mem_peak = measure_memory()
    mem_delta = mem_peak - mem_baseline
    
    print(f"Peak memory: {mem_peak:.2f}MB")
    print(f"Memory delta: {mem_delta:.2f}MB")
    print(f"Generation time: {elapsed:.3f}s")
    print(f"Image size: {buf.getbuffer().nbytes / 1024:.1f}KB")
    
    status = "✓ PASS" if mem_delta < 50.0 else "✗ FAIL"
    print(f"Result: {status}")
    
    # Cleanup
    gc.collect()


async def benchmark_streaming_speed():
    """Benchmark image streaming speed."""
    print("\n=== Streaming Speed Benchmark ===")
    print("Target: > 1MB/s transfer speed\n")
    
    # Create 5MB test image
    test_data = b"X" * (5 * 1024 * 1024)
    buf = io.BytesIO(test_data)
    
    streamer = ImageStreamer()
    
    start_time = time.time()
    chunk_count = 0
    total_bytes = 0
    
    async for chunk in streamer.stream_from_buffer(buf):
        chunk_count += 1
        total_bytes += len(chunk)
    
    elapsed = time.time() - start_time
    speed_mbps = total_bytes / (1024 * 1024) / elapsed
    
    print(f"Data size: {total_bytes / (1024 * 1024):.2f}MB")
    print(f"Chunks: {chunk_count}")
    print(f"Time: {elapsed:.3f}s")
    print(f"Speed: {speed_mbps:.2f}MB/s")
    
    status = "✓ PASS" if speed_mbps > 1.0 else "✗ FAIL"
    print(f"Result: {status}")


async def benchmark_concurrent_requests():
    """Benchmark concurrent image generation (5 simultaneous)."""
    print("\n=== Concurrent Requests Benchmark ===")
    print("Target: 5 simultaneous requests without errors\n")
    
    data = pd.DataFrame({
        "category": [f"カテゴリ{i}" for i in range(10)],
        "amount": [10000 + i * 1000 for i in range(10)]
    })
    
    async def generate_image(task_id: int):
        """Generate an image (simulates concurrent request)."""
        generator = ChartGenerator()
        start = time.time()
        buf = generator.create_monthly_pie_chart(data, f"並行処理テスト{task_id}")
        elapsed = time.time() - start
        return task_id, elapsed, buf.getbuffer().nbytes
    
    # Run 5 concurrent generations
    start_time = time.time()
    tasks = [generate_image(i) for i in range(5)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    total_elapsed = time.time() - start_time
    
    print(f"Total time: {total_elapsed:.3f}s")
    print(f"Average per request: {total_elapsed / 5:.3f}s\n")
    
    success_count = 0
    for result in results:
        if isinstance(result, Exception):
            print(f"Task error: {result}")
        else:
            task_id, elapsed, size = result
            print(f"Task {task_id}: {elapsed:.3f}s | {size / 1024:.1f}KB")
            success_count += 1
    
    status = "✓ PASS" if success_count == 5 else "✗ FAIL"
    print(f"\nResult: {success_count}/5 succeeded | {status}")


def main():
    """Run all benchmarks."""
    print("=" * 60)
    print("TASK-607 Performance Benchmark")
    print("=" * 60)
    
    # Check dependencies
    try:
        from household_mcp.visualization.chart_generator import HAS_VISUALIZATION_DEPS
        if not HAS_VISUALIZATION_DEPS:
            print("Error: Visualization dependencies not installed")
            print("Install with: uv pip install -e '.[visualization]'")
            return 1
    except ImportError as e:
        print(f"Error: Failed to import modules: {e}")
        return 1
    
    # Run synchronous benchmarks
    benchmark_image_generation()
    benchmark_memory_usage()
    
    # Run async benchmarks
    asyncio.run(benchmark_streaming_speed())
    asyncio.run(benchmark_concurrent_requests())
    
    print("\n" + "=" * 60)
    print("Benchmark complete!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
