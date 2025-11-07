"""互換性レイヤーのテスト。

DataLoaderAdapter が CSV バックエンドと SQLite バックエンドの両方で
期待通りに動作することを検証します。
"""

from datetime import datetime, timedelta

import pytest

from household_mcp.database import Transaction
from household_mcp.database.manager import DatabaseManager
from household_mcp.dataloader_compat import CSVBackend, DataLoaderAdapter, SQLiteBackend


class TestCSVBackend:
    """CSV バックエンド機能テスト。"""

    def test_csv_backend_load_month(self):
        """CSV バックエンドで月データを読み込める。"""
        # CSV ファイルが存在することを前提（data/ ディレクトリ使用）
        backend = CSVBackend(src_dir="data")

        # 利用可能な月を列挙
        months = list(backend.iter_available_months())
        assert len(months) > 0, "利用可能な月が見つかりません"

        # 最初の月のデータを読み込む
        year, month = months[0]
        df = backend.load_month(year, month)

        assert not df.empty, f"月データが空です ({year}-{month})"
        assert "金額（円）" in df.columns
        assert "日付" in df.columns
        assert "大項目" in df.columns
        assert "中項目" in df.columns

    def test_csv_backend_cache_stats(self):
        """CSV バックエンドのキャッシュ統計が正常に動作。"""
        backend = CSVBackend(src_dir="data")
        stats = backend.cache_stats()

        assert "hits" in stats
        assert "misses" in stats
        assert "size" in stats
        assert stats["hits"] >= 0
        assert stats["misses"] >= 0


class TestSQLiteBackend:
    """SQLite バックエンド機能テスト。"""

    @pytest.fixture
    def db_manager(self):
        """テスト用のデータベース マネージャー。"""
        manager = DatabaseManager()
        # テスト用に既存テーブルを削除して再作成
        manager.drop_all_tables()
        manager.initialize_database()
        yield manager
        # テスト終了後もクリーンアップ
        manager.drop_all_tables()

    @pytest.fixture
    def sample_transactions(self):
        """テスト用の取引レコード。"""
        base_date = datetime(2024, 1, 1)
        return [
            {
                "source_file": "test.csv",
                "row_number": i,
                "date": base_date + timedelta(days=i),
                "amount": -1000 - i * 100,
                "category_major": "食費" if i % 2 == 0 else "交通費",
                "category_minor": "外食" if i % 2 == 0 else "電車",
                "description": f"テスト取引 {i}",
            }
            for i in range(10)
        ]

    def test_sqlite_backend_load_month(self, db_manager, sample_transactions):
        """SQLite バックエンドで月データを読み込める。"""
        session = db_manager.get_session()
        try:
            # テスト用取引を追加
            for tx_data in sample_transactions:
                tx = Transaction(**tx_data)
                session.add(tx)
            session.commit()

            backend = SQLiteBackend(session=session)

            # 利用可能な月を確認
            months = list(backend.iter_available_months())
            if months:
                year, month = months[0]
                df = backend.load_month(year, month)

                assert "金額（円）" in df.columns
                assert "大項目" in df.columns
                assert "中項目" in df.columns
                assert len(df) > 0
        finally:
            session.close()

    def test_sqlite_backend_cache_stats(self, db_manager):
        """SQLite バックエンドのキャッシュ統計が正常に動作。"""
        session = db_manager.get_session()
        try:
            backend = SQLiteBackend(session=session)
            stats = backend.cache_stats()

            assert "hits" in stats
            assert "misses" in stats
            assert "size" in stats
        finally:
            session.close()


class TestDataLoaderAdapter:
    """DataLoaderAdapter 統合テスト。"""

    def test_adapter_csv_backend(self):
        """DataLoaderAdapter が CSV バックエンドで動作。"""
        adapter = DataLoaderAdapter(backend_type="csv", csv_dir="data")

        assert adapter.backend_type == "csv"

        # 利用可能な月を列挙
        months = list(adapter.iter_available_months())
        assert len(months) > 0

    def test_adapter_sqlite_backend(self):
        """DataLoaderAdapter が SQLite バックエンドで動作。"""
        adapter = DataLoaderAdapter(backend_type="sqlite")

        assert adapter.backend_type == "sqlite"

    def test_adapter_invalid_backend(self):
        """不正なバックエンドタイプでエラーが発生。"""
        with pytest.raises(ValueError):
            DataLoaderAdapter(backend_type="invalid")

    def test_adapter_csv_consistency(self):
        """CSV バックエンドの結果が一貫している。"""
        adapter = DataLoaderAdapter(backend_type="csv", csv_dir="data")

        months = list(adapter.iter_available_months())
        if months:
            year, month = months[0]

            # 同じ月を複数回読み込む
            df1 = adapter.load_month(year, month)
            df2 = adapter.load_month(year, month)

            # キャッシュが効いているか確認
            stats = adapter.cache_stats()
            assert stats["hits"] >= 1, "キャッシュが効いていません"

            # データが同じ
            assert len(df1) == len(df2)

    def test_adapter_category_hierarchy(self):
        """カテゴリ階層が正しく取得できる。"""
        adapter = DataLoaderAdapter(backend_type="csv", csv_dir="data")

        months = list(adapter.iter_available_months())
        if months:
            year, month = months[0]
            hierarchy = adapter.category_hierarchy(year=year, month=month)

            assert isinstance(hierarchy, dict)
            assert len(hierarchy) > 0

            # 各カテゴリがリスト形式
            for key, value in hierarchy.items():
                assert isinstance(value, list)

    def test_adapter_load_many(self):
        """複数月を読み込める。"""
        adapter = DataLoaderAdapter(backend_type="csv", csv_dir="data")

        months = list(adapter.iter_available_months())
        if len(months) >= 2:
            # 最初の 2 ヶ月を読み込む
            df = adapter.load_many(months[:2])

            assert not df.empty
            assert len(df) > 0

    def test_adapter_clear_cache(self):
        """キャッシュが正しくクリアできる。"""
        adapter = DataLoaderAdapter(backend_type="csv", csv_dir="data")

        # キャッシュを生成
        months = list(adapter.iter_available_months())
        if months:
            year, month = months[0]
            adapter.load_month(year, month)

            # キャッシュをクリア
            adapter.clear_cache()
            stats = adapter.cache_stats()

            assert stats["size"] == 0
            assert stats["hits"] == 0
            assert stats["misses"] == 0
