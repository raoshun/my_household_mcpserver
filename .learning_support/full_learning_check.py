#!/usr/bin/env python3
"""
学習支援システム - 統合学習チェックモジュール
"""

import json
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from understanding_checker import LearningDataManager, UnderstandingLevel, TDDProficiency
from learning_path_generator import LearningPathGenerator
from review_scheduler import ReviewScheduler
from tdd_tracker import TDDTracker
from changelog_helper import ChangelogHelper

class FullLearningCheck:
    def __init__(self):
        self.data_manager = LearningDataManager()
        self.path_generator = LearningPathGenerator()
        self.scheduler = ReviewScheduler()
        self.tdd_tracker = TDDTracker()
        self.changelog_helper = ChangelogHelper()
    
    def run_full_check(self, concept: str = None):
        """完全な学習チェックを実行"""
        print("=" * 60)
        print("🎓 学習支援システム - 完全チェック")
        print("=" * 60)
        
        # 1. 概念レベルの確認
        if concept:
            self._check_single_concept(concept)
        else:
            self._check_all_concepts()
        
        # 2. 復習スケジュールの確認
        self._check_review_schedule()
        
        # 3. TDD実践状況の確認
        self._check_tdd_practice()
        
        # 4. バージョン管理状況の確認
        self._check_version_management()
        
        # 5. 総合的な推奨事項を表示
        self._display_recommendations()
    
    def _check_single_concept(self, concept: str):
        """単一概念の詳細チェック"""
        print(f"\n📋 概念別詳細チェック: {concept}")
        print("-" * 40)
        
        # 理解度確認
        concept_record = self.data_manager.get_concept_record(concept)
        if concept_record:
            self._display_concept_status(concept_record)
        else:
            print(f"❌ 概念 '{concept}' の記録が見つかりません")
            print(f"💡 まず理解度確認を実施してください")
            return
        
        # 学習パスの確認
        self._check_learning_path(concept)
        
        # TDD実践状況の確認
        self._check_concept_tdd_practice(concept)
        
        # 復習スケジュールの確認
        self._check_concept_review_schedule(concept)
    
    def _check_all_concepts(self):
        """全概念の概要チェック"""
        print(f"\n📋 全概念概要チェック")
        print("-" * 40)
        
        if "concepts" not in self.data_manager.data or not self.data_manager.data["concepts"]:
            print("❌ 学習記録がありません")
            print("💡 まず理解度確認を実施してください")
            return
        
        # 概念別サマリー
        concepts_summary = self._get_concepts_summary()
        
        print(f"📊 学習済み概念: {len(concepts_summary)}個")
        
        # 理解度分布
        understanding_distribution = self._get_understanding_distribution(concepts_summary)
        print(f"\n📈 理解度分布:")
        for level, count in understanding_distribution.items():
            print(f"   {level}: {count}個")
        
        # TDD実践度分布
        tdd_distribution = self._get_tdd_distribution(concepts_summary)
        print(f"\n📈 TDD実践度分布:")
        for level, count in tdd_distribution.items():
            print(f"   {level}: {count}個")
        
        # 要注意概念
        attention_needed = self._get_attention_needed_concepts(concepts_summary)
        if attention_needed:
            print(f"\n⚠️  要注意概念 ({len(attention_needed)}個):")
            for concept in attention_needed:
                print(f"   • {concept}")
    
    def _check_review_schedule(self):
        """復習スケジュールの確認"""
        print(f"\n📅 復習スケジュール確認")
        print("-" * 40)
        
        due_reviews = self.scheduler.check_due_reviews()
        
        if not due_reviews:
            print("✅ 現在期限の到来した復習項目はありません")
        else:
            print(f"📅 期限到来復習項目: {len(due_reviews)}個")
            
            # 優先度別に表示
            high_priority = [r for r in due_reviews if r.priority >= 4]
            medium_priority = [r for r in due_reviews if r.priority == 3]
            low_priority = [r for r in due_reviews if r.priority <= 2]
            
            if high_priority:
                print(f"   🔴 高優先度: {len(high_priority)}個")
            if medium_priority:
                print(f"   🟡 中優先度: {len(medium_priority)}個")
            if low_priority:
                print(f"   🟢 低優先度: {len(low_priority)}個")
    
    def _check_tdd_practice(self):
        """TDD実践状況の確認"""
        print(f"\n🔄 TDD実践状況確認")
        print("-" * 40)
        
        if "tdd_records" not in self.data_manager.data or not self.data_manager.data["tdd_records"]:
            print("❌ TDD実践記録がありません")
            print("💡 TDD実践を開始してください")
            return
        
        tdd_records = self.data_manager.data["tdd_records"]
        
        # 全体統計
        total_practices = len(tdd_records)
        success_count = sum(1 for record in tdd_records if record["success"])
        success_rate = success_count / total_practices if total_practices > 0 else 0
        
        print(f"📊 TDD実践統計:")
        print(f"   総実践回数: {total_practices}")
        print(f"   成功率: {success_rate:.1%}")
        
        # フェーズ別統計
        phase_stats = self._get_tdd_phase_stats(tdd_records)
        print(f"   フェーズ別成功率:")
        for phase, stats in phase_stats.items():
            print(f"     {phase.upper()}: {stats['success_rate']:.1%} ({stats['count']}回)")
        
        # 最近の実践状況
        recent_records = [r for r in tdd_records if 
                         datetime.fromisoformat(r["timestamp"]) > datetime.now() - timedelta(days=7)]
        
        if recent_records:
            print(f"   最近7日間: {len(recent_records)}回実践")
        else:
            print(f"   ⚠️  最近7日間の実践記録がありません")
    
    def _check_version_management(self):
        """バージョン管理状況の確認"""
        print(f"\n📦 バージョン管理確認")
        print("-" * 40)
        
        # 変更フラグメントの確認
        fragments = self.changelog_helper.list_fragments()
        
        total_fragments = sum(len(items) for items in fragments.values())
        
        if total_fragments == 0:
            print("❌ 変更フラグメントがありません")
            print("💡 変更を行った際はフラグメントを作成してください")
        else:
            print(f"📋 変更フラグメント: {total_fragments}個")
            
            for ftype, items in fragments.items():
                if items:
                    print(f"   {self.changelog_helper.fragment_types[ftype]}: {len(items)}個")
            
            # バージョンアップの提案
            version_bump = self.changelog_helper.suggest_version_bump()
            print(f"💡 推奨バージョンアップ: {version_bump}")
    
    def _display_recommendations(self):
        """総合的な推奨事項を表示"""
        print(f"\n💡 総合推奨事項")
        print("=" * 60)
        
        recommendations = self._generate_recommendations()
        
        if not recommendations:
            print("✅ 現在推奨事項はありません。良い状態です！")
            return
        
        for i, recommendation in enumerate(recommendations, 1):
            print(f"{i}. {recommendation['title']}")
            print(f"   説明: {recommendation['description']}")
            print(f"   アクション: {recommendation['action']}")
            print(f"   優先度: {recommendation['priority']}")
            print()
    
    def _generate_recommendations(self) -> List[Dict[str, str]]:
        """推奨事項を生成"""
        recommendations = []
        
        # 理解度確認が必要な概念
        concepts_needing_check = self._get_concepts_needing_understanding_check()
        if concepts_needing_check:
            recommendations.append({
                "title": "理解度確認が必要",
                "description": f"{len(concepts_needing_check)}個の概念で理解度確認が必要です",
                "action": "理解度確認ツールを実行してください",
                "priority": "高"
            })
        
        # 期限到来復習項目
        due_reviews = self.scheduler.check_due_reviews()
        if due_reviews:
            high_priority_reviews = [r for r in due_reviews if r.priority >= 4]
            if high_priority_reviews:
                recommendations.append({
                    "title": "高優先度復習項目",
                    "description": f"{len(high_priority_reviews)}個の高優先度復習項目があります",
                    "action": "復習スケジューラーを実行してください",
                    "priority": "高"
                })
        
        # TDD実践不足
        recent_tdd_count = self._get_recent_tdd_count()
        if recent_tdd_count < 3:
            recommendations.append({
                "title": "TDD実践不足",
                "description": "最近のTDD実践が不足しています",
                "action": "TDDサイクルを実践してください",
                "priority": "中"
            })
        
        # 変更フラグメント不足
        fragments = self.changelog_helper.list_fragments()
        total_fragments = sum(len(items) for items in fragments.values())
        if total_fragments == 0:
            recommendations.append({
                "title": "変更フラグメント不足",
                "description": "変更フラグメントが作成されていません",
                "action": "変更を行った際はフラグメントを作成してください",
                "priority": "低"
            })
        
        return recommendations
    
    def _display_concept_status(self, concept_record):
        """概念の状態を表示"""
        print(f"📊 概念状況:")
        print(f"   理解度: {concept_record.understanding_level.value}")
        print(f"   TDD実践度: {concept_record.tdd_proficiency.value}")
        print(f"   最終確認: {concept_record.last_confirmed.strftime('%Y-%m-%d')}")
        print(f"   実装回数: {concept_record.implementation_count}")
        print(f"   エラー回数: {concept_record.error_count}")
        
        if concept_record.implementation_count > 0:
            error_rate = concept_record.error_count / concept_record.implementation_count
            print(f"   エラー率: {error_rate:.1%}")
    
    def _check_learning_path(self, concept: str):
        """学習パスの確認"""
        if "learning_paths" not in self.data_manager.data:
            print(f"📚 学習パス: 未生成")
            return
        
        if concept in self.data_manager.data["learning_paths"]:
            learning_path = self.data_manager.data["learning_paths"][concept]
            print(f"📚 学習パス: 生成済み")
            print(f"   総推定時間: {learning_path['total_estimated_time']}分")
            print(f"   ステップ数: {len(learning_path['steps'])}個")
        else:
            print(f"📚 学習パス: 未生成")
    
    def _check_concept_tdd_practice(self, concept: str):
        """概念のTDD実践状況確認"""
        summary = self.tdd_tracker.get_tdd_summary(concept)
        
        if summary["total_records"] == 0:
            print(f"🔄 TDD実践: 未実施")
        else:
            print(f"🔄 TDD実践: {summary['total_records']}回 (成功率: {summary['success_rate']:.1%})")
    
    def _check_concept_review_schedule(self, concept: str):
        """概念の復習スケジュール確認"""
        if "review_schedule" not in self.data_manager.data:
            print(f"📅 復習スケジュール: 未設定")
            return
        
        if concept in self.data_manager.data["review_schedule"]:
            review_data = self.data_manager.data["review_schedule"][concept]
            next_review = datetime.fromisoformat(review_data["next_review_date"])
            
            if next_review <= datetime.now():
                print(f"📅 復習スケジュール: 期限到来")
            else:
                days_until = (next_review - datetime.now()).days
                print(f"📅 復習スケジュール: {days_until}日後")
        else:
            print(f"📅 復習スケジュール: 未設定")
    
    def _get_concepts_summary(self) -> List[Dict[str, Any]]:
        """概念サマリーを取得"""
        summary = []
        
        for concept, data in self.data_manager.data["concepts"].items():
            summary.append({
                "concept": concept,
                "understanding_level": data["understanding_level"],
                "tdd_proficiency": data["tdd_proficiency"],
                "last_confirmed": datetime.fromisoformat(data["last_confirmed"]),
                "implementation_count": data["implementation_count"],
                "error_count": data["error_count"]
            })
        
        return summary
    
    def _get_understanding_distribution(self, concepts_summary: List[Dict[str, Any]]) -> Dict[str, int]:
        """理解度分布を取得"""
        distribution = {}
        
        for concept in concepts_summary:
            level = concept["understanding_level"]
            distribution[level] = distribution.get(level, 0) + 1
        
        return distribution
    
    def _get_tdd_distribution(self, concepts_summary: List[Dict[str, Any]]) -> Dict[str, int]:
        """TDD実践度分布を取得"""
        distribution = {}
        
        for concept in concepts_summary:
            level = concept["tdd_proficiency"]
            distribution[level] = distribution.get(level, 0) + 1
        
        return distribution
    
    def _get_attention_needed_concepts(self, concepts_summary: List[Dict[str, Any]]) -> List[str]:
        """要注意概念を取得"""
        attention_needed = []
        
        for concept in concepts_summary:
            # 理解度が低い
            if concept["understanding_level"] in ["not_assessed", "beginner"]:
                attention_needed.append(concept["concept"])
            # エラー率が高い
            elif concept["implementation_count"] > 0:
                error_rate = concept["error_count"] / concept["implementation_count"]
                if error_rate > 0.3:
                    attention_needed.append(concept["concept"])
            # 長期間確認していない
            elif datetime.now() - concept["last_confirmed"] > timedelta(days=60):
                attention_needed.append(concept["concept"])
        
        return attention_needed
    
    def _get_tdd_phase_stats(self, tdd_records: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """TDDフェーズ別統計を取得"""
        stats = {}
        
        for phase in ["red", "green", "refactor"]:
            phase_records = [r for r in tdd_records if r["phase"] == phase]
            success_count = sum(1 for r in phase_records if r["success"])
            
            stats[phase] = {
                "count": len(phase_records),
                "success_count": success_count,
                "success_rate": success_count / len(phase_records) if phase_records else 0
            }
        
        return stats
    
    def _get_concepts_needing_understanding_check(self) -> List[str]:
        """理解度確認が必要な概念を取得"""
        if "concepts" not in self.data_manager.data:
            return []
        
        concepts_needing_check = []
        
        for concept, data in self.data_manager.data["concepts"].items():
            last_confirmed = datetime.fromisoformat(data["last_confirmed"])
            
            # 30日以上確認していない
            if datetime.now() - last_confirmed > timedelta(days=30):
                concepts_needing_check.append(concept)
        
        return concepts_needing_check
    
    def _get_recent_tdd_count(self) -> int:
        """最近のTDD実践回数を取得"""
        if "tdd_records" not in self.data_manager.data:
            return 0
        
        recent_records = [
            r for r in self.data_manager.data["tdd_records"]
            if datetime.fromisoformat(r["timestamp"]) > datetime.now() - timedelta(days=7)
        ]
        
        return len(recent_records)

def main():
    concept = sys.argv[1] if len(sys.argv) > 1 else None
    
    checker = FullLearningCheck()
    checker.run_full_check(concept)

if __name__ == "__main__":
    main()
