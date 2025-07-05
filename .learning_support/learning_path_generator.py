#!/usr/bin/env python3
"""
学習支援システム - 学習パス生成モジュール
"""

import json
import sys
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from understanding_checker import LearningDataManager, UnderstandingLevel, TDDProficiency

@dataclass
class LearningStep:
    step: int
    concept: str
    estimated_time: int  # 分
    learning_method: str
    practice_exercises: List[str]
    validation_criteria: List[str]
    dependencies: List[str]

@dataclass
class LearningPath:
    target_concept: str
    identified_gap: str
    starting_point: str
    steps: List[LearningStep]
    total_estimated_time: int
    learning_style: str
    created_at: str

class LearningPathGenerator:
    def __init__(self):
        self.data_manager = LearningDataManager()
        self.knowledge_graph = self._build_knowledge_graph()
    
    def _build_knowledge_graph(self) -> Dict[str, Dict[str, Any]]:
        """知識依存関係グラフを構築"""
        return {
            "CSVリーダー": {
                "prerequisites": ["Pythonの基本文法", "ファイル操作", "pandasライブラリ"],
                "difficulty": "beginner",
                "estimated_time": 120,
                "learning_methods": {
                    "visual": "フローチャートと実装例",
                    "auditory": "口頭説明とディスカッション",
                    "kinesthetic": "実際のコーディング",
                    "logical": "段階的な理論構築"
                }
            },
            "pandasライブラリ": {
                "prerequisites": ["Pythonの基本文法"],
                "difficulty": "intermediate",
                "estimated_time": 90,
                "learning_methods": {
                    "visual": "データフレーム図表",
                    "auditory": "操作方法の説明",
                    "kinesthetic": "実際のデータ操作",
                    "logical": "体系的なメソッド学習"
                }
            },
            "ファイル操作": {
                "prerequisites": ["Pythonの基本文法"],
                "difficulty": "beginner",
                "estimated_time": 60,
                "learning_methods": {
                    "visual": "ファイル構造図",
                    "auditory": "ファイルI/Oの説明",
                    "kinesthetic": "ファイル読み書き演習",
                    "logical": "ファイルAPIの体系的理解"
                }
            },
            "Pythonの基本文法": {
                "prerequisites": [],
                "difficulty": "beginner",
                "estimated_time": 90,
                "learning_methods": {
                    "visual": "構文図",
                    "auditory": "文法説明",
                    "kinesthetic": "サンプルコード演習",
                    "logical": "文法体系の整理"
                }
            },
            "SQLiteデータベース": {
                "prerequisites": ["データベースの基本概念", "SQL基本構文"],
                "difficulty": "intermediate",
                "estimated_time": 150,
                "learning_methods": {
                    "visual": "ER図とテーブル設計",
                    "auditory": "SQLクエリの説明",
                    "kinesthetic": "実際のデータベース操作",
                    "logical": "正規化理論"
                }
            },
            "SQL基本構文": {
                "prerequisites": ["データベースの基本概念"],
                "difficulty": "beginner",
                "estimated_time": 60,
                "learning_methods": {
                    "visual": "SQL文例一覧",
                    "auditory": "クエリ説明",
                    "kinesthetic": "クエリ演習",
                    "logical": "構文規則の整理"
                }
            },
            "データベースの基本概念": {
                "prerequisites": [],
                "difficulty": "beginner",
                "estimated_time": 45,
                "learning_methods": {
                    "visual": "リレーショナル図",
                    "auditory": "概念説明",
                    "kinesthetic": "簡単なDB設計演習",
                    "logical": "データ構造の体系化"
                }
            },
            "SQLiteの複雑なJOINクエリ": {
                "prerequisites": ["SQLiteデータベース", "SQLiteの基本的なJOIN"],
                "difficulty": "advanced",
                "estimated_time": 180,
                "learning_methods": {
                    "visual": "JOIN操作の図解",
                    "auditory": "クエリ実行計画の説明",
                    "kinesthetic": "複雑なクエリ作成",
                    "logical": "クエリ最適化理論"
                }
            },
            "SQLiteの基本的なJOIN": {
                "prerequisites": ["SQL基本構文"],
                "difficulty": "intermediate",
                "estimated_time": 60,
                "learning_methods": {
                    "visual": "JOIN図",
                    "auditory": "JOINの説明",
                    "kinesthetic": "JOINクエリ演習",
                    "logical": "JOIN理論"
                }
            },
            "MCPサーバ": {
                "prerequisites": ["Pythonの基本文法", "非同期プログラミング", "JSON操作"],
                "difficulty": "advanced",
                "estimated_time": 240,
                "learning_methods": {
                    "visual": "アーキテクチャ図",
                    "auditory": "通信プロトコルの説明",
                    "kinesthetic": "実際のサーバ実装",
                    "logical": "プロトコル仕様"
                }
            },
            "非同期プログラミング": {
                "prerequisites": ["Pythonの基本文法"],
                "difficulty": "intermediate",
                "estimated_time": 90,
                "learning_methods": {
                    "visual": "async/awaitフロー図",
                    "auditory": "非同期処理の説明",
                    "kinesthetic": "asyncio演習",
                    "logical": "イベントループ理論"
                }
            },
            "JSON操作": {
                "prerequisites": ["Pythonの基本文法"],
                "difficulty": "beginner",
                "estimated_time": 30,
                "learning_methods": {
                    "visual": "JSON構造例",
                    "auditory": "データ交換説明",
                    "kinesthetic": "jsonモジュール演習",
                    "logical": "データ構造の整理"
                }
            },
            "TDD実践": {
                "prerequisites": ["テストの基本概念", "pytest"],
                "difficulty": "intermediate",
                "estimated_time": 120,
                "learning_methods": {
                    "visual": "TDDサイクル図",
                    "auditory": "ペアプログラミング",
                    "kinesthetic": "実際のテスト作成",
                    "logical": "テスト戦略"
                }
            },
            "テストの基本概念": {
                "prerequisites": [],
                "difficulty": "beginner",
                "estimated_time": 30,
                "learning_methods": {
                    "visual": "テストピラミッド図",
                    "auditory": "テストの意義説明",
                    "kinesthetic": "簡単なテスト作成",
                    "logical": "テスト分類の整理"
                }
            },
            "pytest": {
                "prerequisites": ["Pythonの基本文法"],
                "difficulty": "beginner",
                "estimated_time": 30,
                "learning_methods": {
                    "visual": "pytest構文例",
                    "auditory": "pytestの使い方説明",
                    "kinesthetic": "pytest演習",
                    "logical": "テスト自動化の理論"
                }
            }
        }
    
    def _analyze_progress_and_adjust(self, target_concept: str, steps: List[LearningStep]) -> List[LearningStep]:
        """エラー率や進捗に応じて学習パスや推定時間を動的に調整"""
        record = self.data_manager.get_concept_record(target_concept)
        if not record:
            return steps
        # エラー率 = error_count / max(1, implementation_count)
        error_rate = record.error_count / max(1, record.implementation_count)
        # エラー率が高い場合は全ステップの推定時間を1.5倍にし、基礎的な演習を追加
        if error_rate > 0.3:
            for step in steps:
                step.estimated_time = int(step.estimated_time * 1.5)
                if "基礎" not in step.practice_exercises[0]:
                    step.practice_exercises.insert(0, f"{step.concept}の基礎復習演習")
        # 実装経験が多くエラー率が低い場合は推定時間を短縮
        elif record.implementation_count >= 5 and error_rate < 0.1:
            for step in steps:
                step.estimated_time = int(step.estimated_time * 0.7)
        return steps

    def _adjust_review_schedule(self, concept: str):
        """エラー率や進捗に応じて復習間隔を自動調整"""
        record = self.data_manager.get_concept_record(concept)
        if not record:
            return
        error_rate = record.error_count / max(1, record.implementation_count)
        schedule = self.data_manager.data.get("review_schedule", {})
        # 基本間隔（単位:日）
        base_intervals = [0, 1, 3, 7, 14, 30, 90]
        # エラー率が高い場合は間隔を短縮
        if error_rate > 0.3:
            intervals = [max(1, int(i * 0.5)) for i in base_intervals]
        # エラー率が低く実装経験豊富なら間隔を延長
        elif record.implementation_count >= 5 and error_rate < 0.1:
            intervals = [int(i * 1.5) for i in base_intervals]
        else:
            intervals = base_intervals
        # スケジュールを更新
        today = str(self._get_today())
        schedule[concept] = [today] + [str(self._add_days(today, d)) for d in intervals[1:]]
        self.data_manager.data["review_schedule"] = schedule
        self.data_manager._save_data()

    def _get_today(self):
        from datetime import datetime
        return datetime.now().date()

    def _add_days(self, date_str, days):
        from datetime import datetime, timedelta
        d = datetime.fromisoformat(date_str)
        return (d + timedelta(days=days)).date()

    def generate_learning_path(self, target_concept: str, learning_style: str = "balanced") -> LearningPath:
        """学習パスを生成（進捗・エラー率に応じて動的調整）"""
        print(f"\n=== 学習パス生成: {target_concept} ===")
        current_record = self.data_manager.get_concept_record(target_concept)
        gap_analysis = self._analyze_knowledge_gap(target_concept, current_record)
        steps = self._generate_learning_steps(gap_analysis, learning_style)
        # 進捗・エラー率に応じて学習パスを調整
        steps = self._analyze_progress_and_adjust(target_concept, steps)
        # 復習間隔も自動調整
        self._adjust_review_schedule(target_concept)
        learning_path = LearningPath(
            target_concept=target_concept,
            identified_gap=gap_analysis["identified_gap"],
            starting_point=gap_analysis["starting_point"],
            steps=steps,
            total_estimated_time=sum(step.estimated_time for step in steps),
            learning_style=learning_style,
            created_at=str(datetime.now())
        )
        self._save_learning_path(learning_path)
        return learning_path
    
    def generate_learning_path(self, target_concept: str, learning_style: str = "balanced") -> LearningPath:
        """学習パスを生成"""
        print(f"\n=== 学習パス生成: {target_concept} ===")
        
        # 現在の理解度を確認
        current_record = self.data_manager.get_concept_record(target_concept)
        
        # ギャップ分析
        gap_analysis = self._analyze_knowledge_gap(target_concept, current_record)
        
        # 学習ステップを生成
        steps = self._generate_learning_steps(gap_analysis, learning_style)
        
        # 学習パスを作成
        learning_path = LearningPath(
            target_concept=target_concept,
            identified_gap=gap_analysis["identified_gap"],
            starting_point=gap_analysis["starting_point"],
            steps=steps,
            total_estimated_time=sum(step.estimated_time for step in steps),
            learning_style=learning_style,
            created_at=str(datetime.now())
        )
        
        # 学習パスを保存
        self._save_learning_path(learning_path)
        
        return learning_path
    
    def _analyze_knowledge_gap(self, target_concept: str, current_record: Optional[Any]) -> Dict[str, Any]:
        """知識ギャップを分析"""
        if target_concept not in self.knowledge_graph:
            return {
                "identified_gap": "未知の概念",
                "starting_point": "基礎から学習",
                "missing_prerequisites": []
            }
        
        target_info = self.knowledge_graph[target_concept]
        missing_prerequisites = []
        
        # 前提知識を確認
        for prereq in target_info["prerequisites"]:
            prereq_record = self.data_manager.get_concept_record(prereq)
            if not prereq_record or prereq_record.understanding_level in [UnderstandingLevel.NOT_ASSESSED, UnderstandingLevel.BEGINNER]:
                missing_prerequisites.append(prereq)
        
        if missing_prerequisites:
            # 最も基本的な前提知識を開始点とする
            starting_point = missing_prerequisites[0]
            identified_gap = f"{target_concept}の前提知識: {', '.join(missing_prerequisites)}"
        else:
            # 直接実装可能
            starting_point = target_concept
            identified_gap = f"{target_concept}の実装スキル"
        
        return {
            "identified_gap": identified_gap,
            "starting_point": starting_point,
            "missing_prerequisites": missing_prerequisites
        }
    
    def _generate_learning_steps(self, gap_analysis: Dict[str, Any], learning_style: str) -> List[LearningStep]:
        """学習ステップを生成"""
        steps = []
        step_counter = 1
        
        # 前提知識の学習ステップ
        for prereq in gap_analysis["missing_prerequisites"]:
            if prereq in self.knowledge_graph:
                step = self._create_learning_step(prereq, step_counter, learning_style)
                steps.append(step)
                step_counter += 1
        
        # ターゲット概念の学習ステップ
        target_step = self._create_learning_step(gap_analysis["starting_point"], step_counter, learning_style)
        steps.append(target_step)
        
        return steps
    
    def _create_learning_step(self, concept: str, step_number: int, learning_style: str) -> LearningStep:
        """個別の学習ステップを作成"""
        if concept not in self.knowledge_graph:
            return LearningStep(
                step=step_number,
                concept=concept,
                estimated_time=60,
                learning_method="基礎学習",
                practice_exercises=["基本的な演習"],
                validation_criteria=["基本理解の確認"],
                dependencies=[]
            )
        
        concept_info = self.knowledge_graph[concept]
        
        # 学習方法を選択
        learning_method = concept_info["learning_methods"].get(learning_style, "バランス型学習")
        
        # 練習問題を生成
        practice_exercises = self._generate_practice_exercises(concept, concept_info["difficulty"])
        
        # 検証基準を生成
        validation_criteria = self._generate_validation_criteria(concept, concept_info["difficulty"])
        
        return LearningStep(
            step=step_number,
            concept=concept,
            estimated_time=concept_info["estimated_time"],
            learning_method=learning_method,
            practice_exercises=practice_exercises,
            validation_criteria=validation_criteria,
            dependencies=concept_info["prerequisites"]
        )
    
    def _generate_practice_exercises(self, concept: str, difficulty: str) -> List[str]:
        """練習問題を生成"""
        exercises_map = {
            "CSVリーダー": [
                "基本的なCSVファイルの読み込み",
                "エラーハンドリングの実装",
                "文字エンコーディングの対応",
                "大きなファイルの処理"
            ],
            "pandasライブラリ": [
                "データフレームの作成と操作",
                "データの絞り込みと集計",
                "データの結合とピボット",
                "データの可視化"
            ],
            "SQLiteデータベース": [
                "テーブルの作成と挿入",
                "基本的なクエリの作成",
                "インデックスの設定",
                "トランザクション処理"
            ],
            "TDD実践": [
                "失敗テストの作成",
                "最小実装の作成",
                "リファクタリングの実施",
                "テストケースの拡張"
            ]
        }
        
        return exercises_map.get(concept, [f"{concept}の基本演習"])
    
    def _generate_validation_criteria(self, concept: str, difficulty: str) -> List[str]:
        """検証基準を生成"""
        criteria_map = {
            "CSVリーダー": [
                "正常なファイルを読み込める",
                "エラーを適切に処理できる",
                "異なるエンコーディングに対応できる",
                "パフォーマンスを考慮できる"
            ],
            "pandasライブラリ": [
                "データフレームを操作できる",
                "データの変換ができる",
                "集計処理ができる",
                "効率的なコードを書ける"
            ],
            "SQLiteデータベース": [
                "テーブル設計ができる",
                "クエリを書ける",
                "パフォーマンスを考慮できる",
                "データの整合性を保てる"
            ],
            "TDD実践": [
                "Red-Green-Refactorサイクルを実践できる",
                "適切なテストを書ける",
                "リファクタリングができる",
                "テストカバレッジを意識できる"
            ]
        }
        
        return criteria_map.get(concept, [f"{concept}の基本的な理解"])
    
    def _save_learning_path(self, learning_path: LearningPath):
        """学習パスを保存"""
        if "learning_paths" not in self.data_manager.data:
            self.data_manager.data["learning_paths"] = {}
        
        self.data_manager.data["learning_paths"][learning_path.target_concept] = asdict(learning_path)
        self.data_manager._save_data()
    
    def display_learning_path(self, learning_path: LearningPath):
        """学習パスを表示"""
        print(f"\n=== 学習パス: {learning_path.target_concept} ===")
        print(f"特定されたギャップ: {learning_path.identified_gap}")
        print(f"開始点: {learning_path.starting_point}")
        print(f"総推定時間: {learning_path.total_estimated_time}分")
        print(f"学習スタイル: {learning_path.learning_style}")
        
        print("\n📋 学習ステップ:")
        for step in learning_path.steps:
            print(f"\n{step.step}. {step.concept}")
            print(f"   推定時間: {step.estimated_time}分")
            print(f"   学習方法: {step.learning_method}")
            print(f"   練習問題: {', '.join(step.practice_exercises[:2])}...")
            print(f"   検証基準: {', '.join(step.validation_criteria[:2])}...")
        
        print(f"\n🎯 次のアクション:")
        print(f"   1. {learning_path.steps[0].concept}の学習を開始")
        print(f"   2. 理解度確認を実施")
        print(f"   3. TDDサイクルを実践")
    
    def check_review_alerts(self):
        """復習期限が到来した概念を自動検出し、リマインドを表示"""
        from datetime import datetime
        today = datetime.now().date()
        schedule = self.data_manager.data.get("review_schedule", {})
        due_concepts = []
        for concept, dates in schedule.items():
            for d in dates:
                try:
                    review_date = datetime.fromisoformat(d).date()
                    if review_date <= today:
                        due_concepts.append(concept)
                        break
                except Exception:
                    continue
        if due_concepts:
            print("\n🔔 復習期限が到来した概念:")
            for c in due_concepts:
                print(f"  - {c}")
            print("\n復習コマンド例: python .learning_support/review_scheduler.py --review <概念名>")
        else:
            print("\n本日復習期限の概念はありません。")

def main():
    if len(sys.argv) < 2:
        print("Usage: python learning_path_generator.py <target_concept> [learning_style] [--check-review]")
        print("Learning styles: visual, auditory, kinesthetic, logical, balanced")
        sys.exit(1)
    
    if '--check-review' in sys.argv:
        generator = LearningPathGenerator()
        generator.check_review_alerts()
        sys.exit(0)
    
    target_concept = sys.argv[1]
    learning_style = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else "balanced"
    
    generator = LearningPathGenerator()
    learning_path = generator.generate_learning_path(target_concept, learning_style)
    generator.display_learning_path(learning_path)

if __name__ == "__main__":
    from datetime import datetime
    main()
