#!/usr/bin/env python3
"""
学習支援システム - 復習スケジュール管理モジュール
"""

import json
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from understanding_checker import LearningDataManager, UnderstandingLevel, TDDProficiency

@dataclass
class ReviewItem:
    concept: str
    review_count: int
    next_review_date: datetime
    last_review_date: datetime
    understanding_level: UnderstandingLevel
    tdd_proficiency: TDDProficiency
    priority: int  # 1-5 (5が最高優先度)
    notes: str

class ReviewScheduler:
    def __init__(self):
        self.data_manager = LearningDataManager()
        self.review_intervals = {
            0: 0,      # 即座
            1: 1,      # 1日後
            2: 3,      # 3日後
            3: 7,      # 1週間後
            4: 14,     # 2週間後
            5: 30,     # 1ヶ月後
            6: 90      # 3ヶ月後
        }
    
    def schedule_review(self, concept: str, force_reschedule: bool = False):
        """復習スケジュールを設定"""
        print(f"\n=== 復習スケジュール設定: {concept} ===")
        
        concept_record = self.data_manager.get_concept_record(concept)
        if not concept_record:
            print(f"❌ 概念 '{concept}' が見つかりません")
            print("先に理解度確認を実施してください")
            return
        
        # 既存の復習スケジュールを確認
        existing_review = self._get_review_item(concept)
        
        if existing_review and not force_reschedule:
            print(f"📅 既存の復習スケジュール:")
            print(f"   次回復習日: {existing_review.next_review_date.strftime('%Y-%m-%d')}")
            print(f"   復習回数: {existing_review.review_count}")
            return
        
        # 新しい復習スケジュールを作成
        review_item = self._create_review_item(concept_record)
        self._save_review_item(review_item)
        
        print(f"✅ 復習スケジュールを設定しました")
        print(f"   次回復習日: {review_item.next_review_date.strftime('%Y-%m-%d')}")
        print(f"   優先度: {review_item.priority}/5")
    
    def check_due_reviews(self) -> List[ReviewItem]:
        """期限の到来した復習項目を確認"""
        due_reviews = []
        
        if "review_schedule" not in self.data_manager.data:
            return due_reviews
        
        current_date = datetime.now()
        
        for concept, review_data in self.data_manager.data["review_schedule"].items():
            next_review = datetime.fromisoformat(review_data["next_review_date"])
            
            if next_review <= current_date:
                review_item = ReviewItem(
                    concept=concept,
                    review_count=review_data["review_count"],
                    next_review_date=next_review,
                    last_review_date=datetime.fromisoformat(review_data["last_review_date"]),
                    understanding_level=UnderstandingLevel(review_data["understanding_level"]),
                    tdd_proficiency=TDDProficiency(review_data["tdd_proficiency"]),
                    priority=review_data["priority"],
                    notes=review_data["notes"]
                )
                due_reviews.append(review_item)
        
        return sorted(due_reviews, key=lambda x: x.priority, reverse=True)
    
    def conduct_review(self, concept: str):
        """復習を実施"""
        print(f"\n=== 復習実施: {concept} ===")
        
        review_item = self._get_review_item(concept)
        if not review_item:
            print(f"❌ 復習スケジュールが見つかりません")
            return
        
        # 復習内容を表示
        self._display_review_content(review_item)
        
        # 復習結果を記録
        self._record_review_result(review_item)
    
    def _create_review_item(self, concept_record) -> ReviewItem:
        """復習項目を作成"""
        # 優先度を計算
        priority = self._calculate_priority(concept_record)
        
        # 次回復習日を計算
        next_review_date = self._calculate_next_review_date(0, concept_record)
        
        return ReviewItem(
            concept=concept_record.concept,
            review_count=0,
            next_review_date=next_review_date,
            last_review_date=datetime.now(),
            understanding_level=concept_record.understanding_level,
            tdd_proficiency=concept_record.tdd_proficiency,
            priority=priority,
            notes=""
        )
    
    def _calculate_priority(self, concept_record) -> int:
        """優先度を計算"""
        priority = 3  # 基本優先度
        
        # 理解度による調整
        if concept_record.understanding_level == UnderstandingLevel.BEGINNER:
            priority += 2
        elif concept_record.understanding_level == UnderstandingLevel.INTERMEDIATE:
            priority += 1
        elif concept_record.understanding_level == UnderstandingLevel.EXPERT:
            priority -= 1
        
        # TDD実践度による調整
        if concept_record.tdd_proficiency == TDDProficiency.BEGINNER:
            priority += 1
        elif concept_record.tdd_proficiency == TDDProficiency.EXPERT:
            priority -= 1
        
        # エラー率による調整
        if concept_record.implementation_count > 0:
            error_rate = concept_record.error_count / concept_record.implementation_count
            if error_rate > 0.3:
                priority += 1
        
        return max(1, min(5, priority))
    
    def _calculate_next_review_date(self, review_count: int, concept_record) -> datetime:
        """次回復習日を計算"""
        # 基本間隔を取得
        base_interval = self.review_intervals.get(min(review_count, 6), 90)
        
        # 個別化要因を考慮
        memory_factor = 1.0
        
        # 理解度による調整
        if concept_record.understanding_level == UnderstandingLevel.BEGINNER:
            memory_factor *= 0.7
        elif concept_record.understanding_level == UnderstandingLevel.EXPERT:
            memory_factor *= 1.5
        
        # TDD実践度による調整
        if concept_record.tdd_proficiency == TDDProficiency.BEGINNER:
            memory_factor *= 0.8
        elif concept_record.tdd_proficiency == TDDProficiency.EXPERT:
            memory_factor *= 1.3
        
        # エラー率による調整
        if concept_record.implementation_count > 0:
            error_rate = concept_record.error_count / concept_record.implementation_count
            if error_rate > 0.3:
                memory_factor *= 0.6
        
        # 最終間隔を計算
        adjusted_interval = max(1, int(base_interval * memory_factor))
        
        return datetime.now() + timedelta(days=adjusted_interval)
    
    def _get_review_item(self, concept: str) -> Optional[ReviewItem]:
        """復習項目を取得"""
        if "review_schedule" not in self.data_manager.data:
            return None
        
        if concept not in self.data_manager.data["review_schedule"]:
            return None
        
        review_data = self.data_manager.data["review_schedule"][concept]
        return ReviewItem(
            concept=concept,
            review_count=review_data["review_count"],
            next_review_date=datetime.fromisoformat(review_data["next_review_date"]),
            last_review_date=datetime.fromisoformat(review_data["last_review_date"]),
            understanding_level=UnderstandingLevel(review_data["understanding_level"]),
            tdd_proficiency=TDDProficiency(review_data["tdd_proficiency"]),
            priority=review_data["priority"],
            notes=review_data["notes"]
        )
    
    def _save_review_item(self, review_item: ReviewItem):
        """復習項目を保存"""
        if "review_schedule" not in self.data_manager.data:
            self.data_manager.data["review_schedule"] = {}
        
        self.data_manager.data["review_schedule"][review_item.concept] = {
            "review_count": review_item.review_count,
            "next_review_date": review_item.next_review_date.isoformat(),
            "last_review_date": review_item.last_review_date.isoformat(),
            "understanding_level": review_item.understanding_level.value,
            "tdd_proficiency": review_item.tdd_proficiency.value,
            "priority": review_item.priority,
            "notes": review_item.notes
        }
        
        self.data_manager._save_data()
    
    def _display_review_content(self, review_item: ReviewItem):
        """復習内容を表示"""
        print(f"📚 復習内容: {review_item.concept}")
        print(f"前回復習: {review_item.last_review_date.strftime('%Y-%m-%d')}")
        print(f"復習回数: {review_item.review_count}")
        print(f"現在の理解度: {review_item.understanding_level.value}")
        print(f"現在のTDD実践度: {review_item.tdd_proficiency.value}")
        
        # 復習のポイントを表示
        print(f"\n🎯 復習のポイント:")
        if review_item.understanding_level == UnderstandingLevel.BEGINNER:
            print("   - 基本概念の再確認")
            print("   - 簡単な演習問題")
        elif review_item.understanding_level == UnderstandingLevel.INTERMEDIATE:
            print("   - 実践的な応用例")
            print("   - 問題解決パターン")
        else:
            print("   - 最新の知識アップデート")
            print("   - 最適化のポイント")
    
    def _record_review_result(self, review_item: ReviewItem):
        """復習結果を記録"""
        print(f"\n復習結果を記録します:")
        
        # 復習の成果を確認
        success_input = input("復習は成功しましたか？ (y/n): ").lower()
        success = success_input in ['y', 'yes', '']
        
        # 理解度の変化を確認
        if success:
            print("理解度に変化はありましたか？")
            print("1: 理解度向上")
            print("2: 変化なし")
            print("3: 理解度低下")
            
            change = input("選択してください (1-3): ")
            
            if change == "1":
                # 理解度向上
                review_item.understanding_level = self._improve_understanding_level(review_item.understanding_level)
            elif change == "3":
                # 理解度低下（忘却）
                review_item.understanding_level = self._decrease_understanding_level(review_item.understanding_level)
        
        # 復習回数を更新
        review_item.review_count += 1
        review_item.last_review_date = datetime.now()
        
        # 次回復習日を計算
        concept_record = self.data_manager.get_concept_record(review_item.concept)
        if concept_record:
            concept_record.understanding_level = review_item.understanding_level
            review_item.next_review_date = self._calculate_next_review_date(review_item.review_count, concept_record)
            self.data_manager.update_concept_record(concept_record)
        
        # 復習結果を保存
        self._save_review_item(review_item)
        
        print(f"✅ 復習結果を記録しました")
        print(f"次回復習日: {review_item.next_review_date.strftime('%Y-%m-%d')}")
    
    def _improve_understanding_level(self, current_level: UnderstandingLevel) -> UnderstandingLevel:
        """理解度を向上"""
        if current_level == UnderstandingLevel.BEGINNER:
            return UnderstandingLevel.INTERMEDIATE
        elif current_level == UnderstandingLevel.INTERMEDIATE:
            return UnderstandingLevel.ADVANCED
        elif current_level == UnderstandingLevel.ADVANCED:
            return UnderstandingLevel.EXPERT
        else:
            return current_level
    
    def _decrease_understanding_level(self, current_level: UnderstandingLevel) -> UnderstandingLevel:
        """理解度を低下"""
        if current_level == UnderstandingLevel.EXPERT:
            return UnderstandingLevel.ADVANCED
        elif current_level == UnderstandingLevel.ADVANCED:
            return UnderstandingLevel.INTERMEDIATE
        elif current_level == UnderstandingLevel.INTERMEDIATE:
            return UnderstandingLevel.BEGINNER
        else:
            return current_level
    
    def display_review_schedule(self):
        """復習スケジュールを表示"""
        due_reviews = self.check_due_reviews()
        
        print(f"\n=== 復習スケジュール ===")
        
        if not due_reviews:
            print("📅 現在期限の到来した復習項目はありません")
            return
        
        print(f"📅 期限の到来した復習項目 ({len(due_reviews)}件):")
        for review in due_reviews:
            overdue_days = (datetime.now() - review.next_review_date).days
            status = "期限超過" if overdue_days > 0 else "期限到来"
            
            print(f"\n   🎯 {review.concept}")
            print(f"      状態: {status} ({overdue_days}日)" if overdue_days > 0 else f"      状態: {status}")
            print(f"      優先度: {review.priority}/5")
            print(f"      理解度: {review.understanding_level.value}")
            print(f"      TDD実践度: {review.tdd_proficiency.value}")
        
        print(f"\n💡 推奨アクション:")
        print(f"   1. 最も優先度の高い項目から復習開始")
        print(f"   2. 理解度確認を併用")
        print(f"   3. 必要に応じて学習パスを再生成")

def main():
    scheduler = ReviewScheduler()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--check":
            scheduler.display_review_schedule()
        elif sys.argv[1] == "--schedule":
            if len(sys.argv) > 2:
                concept = sys.argv[2]
                scheduler.schedule_review(concept)
            else:
                print("Usage: python review_scheduler.py --schedule <concept>")
        elif sys.argv[1] == "--review":
            if len(sys.argv) > 2:
                concept = sys.argv[2]
                scheduler.conduct_review(concept)
            else:
                print("Usage: python review_scheduler.py --review <concept>")
        else:
            print("Usage: python review_scheduler.py [--check|--schedule <concept>|--review <concept>]")
    else:
        scheduler.display_review_schedule()

if __name__ == "__main__":
    main()
