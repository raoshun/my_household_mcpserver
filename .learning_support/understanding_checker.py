#!/usr/bin/env python3
"""
学習支援システム - 理解度確認モジュール
"""

import json
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

class UnderstandingLevel(Enum):
    NOT_ASSESSED = "not_assessed"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class TDDProficiency(Enum):
    NOT_ASSESSED = "not_assessed"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

@dataclass
class ConceptRecord:
    concept: str
    understanding_level: UnderstandingLevel
    tdd_proficiency: TDDProficiency
    last_confirmed: datetime
    implementation_count: int
    error_count: int
    learning_path_completed: bool
    prerequisites: List[str]
    related_concepts: List[str]
    notes: str

class LearningDataManager:
    def __init__(self, data_file: str = ".learning_support/learning_data.json"):
        self.data_file = data_file
        self.data = self._load_data()
        
    def _load_data(self) -> Dict[str, Any]:
        """学習データを読み込む"""
        if not os.path.exists(self.data_file):
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            return {"concepts": {}, "learning_paths": {}, "review_schedule": {}}
        
        with open(self.data_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_data(self):
        """学習データを保存する"""
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2, default=str)
    
    def get_concept_record(self, concept: str) -> Optional[ConceptRecord]:
        """概念のレコードを取得"""
        if concept not in self.data["concepts"]:
            return None
        
        data = self.data["concepts"][concept]
        return ConceptRecord(
            concept=concept,
            understanding_level=UnderstandingLevel(data["understanding_level"]),
            tdd_proficiency=TDDProficiency(data["tdd_proficiency"]),
            last_confirmed=datetime.fromisoformat(data["last_confirmed"]),
            implementation_count=data["implementation_count"],
            error_count=data["error_count"],
            learning_path_completed=data["learning_path_completed"],
            prerequisites=data["prerequisites"],
            related_concepts=data["related_concepts"],
            notes=data["notes"]
        )
    
    def update_concept_record(self, record: ConceptRecord):
        """概念のレコードを更新"""
        self.data["concepts"][record.concept] = asdict(record)
        self.data["concepts"][record.concept]["understanding_level"] = record.understanding_level.value
        self.data["concepts"][record.concept]["tdd_proficiency"] = record.tdd_proficiency.value
        self.data["concepts"][record.concept]["last_confirmed"] = record.last_confirmed.isoformat()
        self._save_data()

class UnderstandingChecker:
    def __init__(self):
        self.data_manager = LearningDataManager()
    
    def check_understanding(self, concept: str) -> bool:
        """理解度確認を実行"""
        print(f"\n=== 理解度確認: {concept} ===")
        
        # 既存レコードを取得
        record = self.data_manager.get_concept_record(concept)
        
        if record and self._should_skip_check(record):
            print(f"✓ 省略条件を満たしています（理解度: {record.understanding_level.value}）")
            return True
        
        # 理解度確認を実行
        understanding_level = self._assess_understanding(concept)
        tdd_proficiency = self._assess_tdd_proficiency(concept)
        
        # 前提知識の確認
        prerequisites = self._check_prerequisites(concept, understanding_level)
        
        # レコードを更新
        if record:
            record.understanding_level = understanding_level
            record.tdd_proficiency = tdd_proficiency
            record.last_confirmed = datetime.now()
            record.prerequisites = prerequisites
        else:
            record = ConceptRecord(
                concept=concept,
                understanding_level=understanding_level,
                tdd_proficiency=tdd_proficiency,
                last_confirmed=datetime.now(),
                implementation_count=0,
                error_count=0,
                learning_path_completed=False,
                prerequisites=prerequisites,
                related_concepts=[],
                notes=""
            )
        
        self.data_manager.update_concept_record(record)
        
        # 結果を表示
        self._display_results(record)
        
        return understanding_level in [UnderstandingLevel.INTERMEDIATE, UnderstandingLevel.ADVANCED, UnderstandingLevel.EXPERT]
    
    def _should_skip_check(self, record: ConceptRecord) -> bool:
        """理解度確認を省略すべきかチェック"""
        if record.understanding_level not in [UnderstandingLevel.ADVANCED, UnderstandingLevel.EXPERT]:
            return False
        
        # 30日以内に確認済み
        if datetime.now() - record.last_confirmed > timedelta(days=30):
            return False
        
        # 実装経験が3回以上
        if record.implementation_count < 3:
            return False
        
        # TDD実践度が上級以上
        if record.tdd_proficiency not in [TDDProficiency.ADVANCED, TDDProficiency.EXPERT]:
            return False
        
        return True
    
    def _assess_understanding(self, concept: str) -> UnderstandingLevel:
        """理解度を評価"""
        print(f"\n{concept}について説明してください:")
        print("1. 基本的な概念")
        print("2. 実装方法")
        print("3. 潜在的な問題点")
        print("4. 最適化のポイント")
        
        while True:
            try:
                level = input("\n理解度を評価してください (1:beginner, 2:intermediate, 3:advanced, 4:expert): ")
                level_map = {
                    "1": UnderstandingLevel.BEGINNER,
                    "2": UnderstandingLevel.INTERMEDIATE,
                    "3": UnderstandingLevel.ADVANCED,
                    "4": UnderstandingLevel.EXPERT
                }
                return level_map[level]
            except KeyError:
                print("1-4の数字を入力してください")
    
    def _assess_tdd_proficiency(self, concept: str) -> TDDProficiency:
        """TDD実践度を評価"""
        print(f"\n{concept}のTDD実践について:")
        print("1. Red-Green-Refactorサイクルを理解している")
        print("2. テストファーストで実装できる")
        print("3. 適切なリファクタリングができる")
        print("4. 他者にTDDを教えることができる")
        
        while True:
            try:
                level = input("\nTDD実践度を評価してください (1:beginner, 2:intermediate, 3:advanced, 4:expert): ")
                level_map = {
                    "1": TDDProficiency.BEGINNER,
                    "2": TDDProficiency.INTERMEDIATE,
                    "3": TDDProficiency.ADVANCED,
                    "4": TDDProficiency.EXPERT
                }
                return level_map[level]
            except KeyError:
                print("1-4の数字を入力してください")
    
    def _check_prerequisites(self, concept: str, understanding_level: UnderstandingLevel) -> List[str]:
        """前提知識を確認"""
        # 概念別の前提知識マップ
        prerequisites_map = {
            "CSVリーダー": ["Pythonの基本文法", "ファイル操作", "pandasライブラリ"],
            "SQLiteデータベース": ["データベースの基本概念", "SQL基本構文", "Python SQLite連携"],
            "MCPサーバ": ["Pythonの基本文法", "非同期プログラミング", "JSON操作"],
            "TDD実践": ["テストの基本概念", "pytest", "モックとスタブ"],
            "バージョン管理": ["Git基本操作", "セマンティックバージョニング", "towncrierツール"]
        }
        
        prerequisites = prerequisites_map.get(concept, [])
        
        if understanding_level == UnderstandingLevel.BEGINNER:
            print(f"\n前提知識の確認が必要です: {', '.join(prerequisites)}")
            # 実際の確認プロセスはここで実装
        
        return prerequisites
    
    def _display_results(self, record: ConceptRecord):
        """結果を表示"""
        print(f"\n=== 理解度確認結果 ===")
        print(f"概念: {record.concept}")
        print(f"理解度: {record.understanding_level.value}")
        print(f"TDD実践度: {record.tdd_proficiency.value}")
        print(f"確認日時: {record.last_confirmed.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"前提知識: {', '.join(record.prerequisites)}")
        
        if record.understanding_level == UnderstandingLevel.BEGINNER:
            print("\n📚 学習パスの生成をお勧めします")
            print("   コマンド: python .learning_support/learning_path_generator.py")
        elif record.understanding_level in [UnderstandingLevel.INTERMEDIATE, UnderstandingLevel.ADVANCED]:
            print("\n✅ 実装を開始できます")
            print("   TDDサイクルを実践してください")
        else:
            print("\n🎓 エキスパートレベルです")
            print("   他者への教授や最適化に取り組んでください")

def main():
    if len(sys.argv) != 2:
        print("Usage: python understanding_checker.py <concept_name>")
        sys.exit(1)
    
    concept = sys.argv[1]
    checker = UnderstandingChecker()
    
    if checker.check_understanding(concept):
        print(f"\n✅ {concept}の理解度確認が完了しました")
    else:
        print(f"\n📚 {concept}の追加学習が必要です")

if __name__ == "__main__":
    main()
