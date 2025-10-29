"""Debug script for duplicate detection."""

import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))  # noqa: E402

from household_mcp.database import DatabaseManager, Transaction  # noqa: E402
from household_mcp.duplicate import DetectionOptions, DuplicateDetector  # noqa: E402


def main() -> None:
    """重複検出のデバッグ."""
    manager = DatabaseManager(db_path=":memory:")
    manager.initialize_database()

    with manager.session_scope() as session:
        # テストデータ作成
        trans3 = Transaction(
            source_file="file1.csv",
            row_number=2,
            date=datetime(2025, 1, 20),
            amount=Decimal("500.00"),
            description="コンビニ",
            category_major="食費",
            is_duplicate=0,
        )
        trans4 = Transaction(
            source_file="file2.csv",
            row_number=2,
            date=datetime(2025, 1, 21),
            amount=Decimal("500.00"),
            description="コンビニ",
            category_major="食費",
            is_duplicate=0,
        )
        session.add_all([trans3, trans4])
        session.commit()

        print("トランザクション:")
        print(f"  trans3: {trans3.date}, {trans3.amount}")
        print(f"  trans4: {trans4.date}, {trans4.amount}")

        # 日付誤差1日まで許容
        options = DetectionOptions(date_tolerance_days=1, min_similarity_score=0.7)
        detector = DuplicateDetector(session, options)

        print("\n検出オプション:")
        print(f"  date_tolerance_days: {options.date_tolerance_days}")
        print(f"  amount_tolerance_abs: {options.amount_tolerance_abs}")
        print(f"  amount_tolerance_pct: {options.amount_tolerance_pct}")
        print(f"  min_similarity_score: {options.min_similarity_score}")

        # デバッグ: _is_potential_duplicate を直接テスト
        print("\n_is_potential_duplicate テスト:")
        is_potential = detector._is_potential_duplicate(trans3, trans4)
        print(f"  結果: {is_potential}")

        # デバッグ: _calculate_similarity を直接テスト
        if is_potential:
            score = detector._calculate_similarity(trans3, trans4)
            print("\n_calculate_similarity テスト:")
            print(f"  スコア: {score}")

        # 実際の検出
        candidates = detector.detect_duplicates()
        print("\n検出結果:")
        print(f"  候補数: {len(candidates)}")
        for t1, t2, score in candidates:
            print(
                f"  - {t1.date} vs {t2.date}, 金額: {t1.amount} vs {t2.amount}, スコア: {score}"
            )

    manager.close()


if __name__ == "__main__":
    main()
