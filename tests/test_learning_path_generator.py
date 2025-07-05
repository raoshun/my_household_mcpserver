import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../.learning_support"))
)
from learning_path_generator import LearningPathGenerator


def test_generate_learning_path_red():
    """RED: 学習パス生成の失敗テスト（未登録概念）"""
    generator = LearningPathGenerator()
    # 未知の概念を指定した場合、ギャップ分析で"未知の概念"となることを期待
    path = generator.generate_learning_path("未登録概念", "logical")
    assert path.identified_gap == "未知の概念"
    assert path.starting_point == "基礎から学習"
    assert path.steps[0].concept == "基礎から学習"


# GREEN/REFACTORはTDDサイクルで順次追加
