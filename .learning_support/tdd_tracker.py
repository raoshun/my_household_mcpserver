#!/usr/bin/env python3
"""
学習支援システム - TDD実践追跡モジュール
"""

import json
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from understanding_checker import LearningDataManager, UnderstandingLevel, TDDProficiency

class TDDPhase(Enum):
    RED = "red"
    GREEN = "green"
    REFACTOR = "refactor"

@dataclass
class TDDRecord:
    concept: str
    phase: TDDPhase
    timestamp: datetime
    test_file: str
    implementation_file: str
    success: bool
    error_message: Optional[str]
    notes: str

class TDDTracker:
    def __init__(self):
        self.data_manager = LearningDataManager()
    
    def record_tdd_practice(self, concept: str, phase: TDDPhase, test_file: str = "", implementation_file: str = "", success: bool = True, error_message: Optional[str] = None, notes: str = ""):
        """TDD実践を記録"""
        print(f"\n=== TDD実践記録: {concept} - {phase.value.upper()}フェーズ ===")
        
        # TDDレコードを作成
        tdd_record = TDDRecord(
            concept=concept,
            phase=phase,
            timestamp=datetime.now(),
            test_file=test_file,
            implementation_file=implementation_file,
            success=success,
            error_message=error_message,
            notes=notes
        )
        
        # 記録を保存
        self._save_tdd_record(tdd_record)
        
        # 概念レコードを更新
        self._update_concept_record(concept, phase, success)
        
        # フェーズ別のガイダンスを表示
        self._display_phase_guidance(phase, success)
        
        # 次のステップを提案
        self._suggest_next_step(concept, phase, success)
    
    def _save_tdd_record(self, record: TDDRecord):
        """TDDレコードを保存"""
        if "tdd_records" not in self.data_manager.data:
            self.data_manager.data["tdd_records"] = []
        
        record_dict = asdict(record)
        record_dict["phase"] = record.phase.value
        record_dict["timestamp"] = record.timestamp.isoformat()
        
        self.data_manager.data["tdd_records"].append(record_dict)
        self.data_manager._save_data()
    
    def _update_concept_record(self, concept: str, phase: TDDPhase, success: bool):
        """概念レコードを更新"""
        concept_record = self.data_manager.get_concept_record(concept)
        
        if concept_record:
            concept_record.implementation_count += 1
            if not success:
                concept_record.error_count += 1
            
            # TDD実践度を更新
            concept_record.tdd_proficiency = self._calculate_tdd_proficiency(concept)
            
            self.data_manager.update_concept_record(concept_record)
    
    def _calculate_tdd_proficiency(self, concept: str) -> TDDProficiency:
        """TDD実践度を計算"""
        if "tdd_records" not in self.data_manager.data:
            return TDDProficiency.BEGINNER
        
        # 該当概念のTDDレコードを取得
        concept_records = [
            record for record in self.data_manager.data["tdd_records"]
            if record["concept"] == concept
        ]
        
        if not concept_records:
            return TDDProficiency.BEGINNER
        
        # 成功率を計算
        success_count = sum(1 for record in concept_records if record["success"])
        success_rate = success_count / len(concept_records)
        
        # 全フェーズの実践を確認
        phases_practiced = set(record["phase"] for record in concept_records)
        complete_cycles = len(phases_practiced) == 3  # Red, Green, Refactor
        
        # 実践度を判定
        if success_rate >= 0.9 and complete_cycles and len(concept_records) >= 10:
            return TDDProficiency.EXPERT
        elif success_rate >= 0.8 and complete_cycles and len(concept_records) >= 5:
            return TDDProficiency.ADVANCED
        elif success_rate >= 0.6 and complete_cycles:
            return TDDProficiency.INTERMEDIATE
        else:
            return TDDProficiency.BEGINNER
    
    def _display_phase_guidance(self, phase: TDDPhase, success: bool):
        """フェーズ別のガイダンスを表示"""
        if phase == TDDPhase.RED:
            if success:
                print("✅ REDフェーズ完了")
                print("📝 失敗テストが正常に作成されました")
                print("🎯 次は最小実装でテストを通してください（GREENフェーズ）")
            else:
                print("❌ REDフェーズでエラー")
                print("📝 テストが期待通りに失敗していません")
                print("🔧 テストの実装を見直してください")
        
        elif phase == TDDPhase.GREEN:
            if success:
                print("✅ GREENフェーズ完了")
                print("📝 テストが通る最小実装が完了しました")
                print("🎯 次はコード品質を向上させてください（REFACTORフェーズ）")
            else:
                print("❌ GREENフェーズでエラー")
                print("📝 テストが通らない状態です")
                print("🔧 実装を見直してテストを通してください")
        
        elif phase == TDDPhase.REFACTOR:
            if success:
                print("✅ REFACTORフェーズ完了")
                print("📝 コード品質が向上しました")
                print("🎯 次の機能のTDDサイクルを開始してください")
            else:
                print("❌ REFACTORフェーズでエラー")
                print("📝 リファクタリング中にテストが失敗しました")
                print("🔧 変更を戻してから再度リファクタリングしてください")
    
    def _suggest_next_step(self, concept: str, phase: TDDPhase, success: bool):
        """次のステップを提案"""
        if not success:
            print(f"\n💡 推奨アクション:")
            print(f"   1. エラーメッセージを確認")
            print(f"   2. 段階的に問題を切り分け")
            print(f"   3. 必要に応じて理解度確認を実施")
            return
        
        if phase == TDDPhase.RED:
            print(f"\n💡 GREENフェーズのヒント:")
            print(f"   1. テストを通す最小限のコードを書く")
            print(f"   2. 完璧な実装を目指さない")
            print(f"   3. まずはハードコーディングでも良い")
        
        elif phase == TDDPhase.GREEN:
            print(f"\n💡 REFACTORフェーズのヒント:")
            print(f"   1. 重複コードを排除")
            print(f"   2. 変数名・関数名を改善")
            print(f"   3. 各リファクタリング後にテストを実行")
        
        elif phase == TDDPhase.REFACTOR:
            print(f"\n💡 次のTDDサイクルのヒント:")
            print(f"   1. 新しい機能や改善点を特定")
            print(f"   2. 失敗テストを作成（REDフェーズ）")
            print(f"   3. 学習記録を更新")
    
    def get_tdd_summary(self, concept: str) -> Dict[str, Any]:
        """TDD実践のサマリーを取得"""
        if "tdd_records" not in self.data_manager.data:
            return {"total_records": 0, "success_rate": 0.0, "phases": {}}
        
        concept_records = [
            record for record in self.data_manager.data["tdd_records"]
            if record["concept"] == concept
        ]
        
        if not concept_records:
            return {"total_records": 0, "success_rate": 0.0, "phases": {}}
        
        # 統計を計算
        total_records = len(concept_records)
        success_count = sum(1 for record in concept_records if record["success"])
        success_rate = success_count / total_records
        
        # フェーズ別統計
        phases = {}
        for phase in TDDPhase:
            phase_records = [record for record in concept_records if record["phase"] == phase.value]
            phases[phase.value] = {
                "count": len(phase_records),
                "success_count": sum(1 for record in phase_records if record["success"]),
                "success_rate": sum(1 for record in phase_records if record["success"]) / len(phase_records) if phase_records else 0.0
            }
        
        return {
            "total_records": total_records,
            "success_rate": success_rate,
            "phases": phases
        }
    
    def display_tdd_summary(self, concept: str):
        """TDD実践のサマリーを表示"""
        summary = self.get_tdd_summary(concept)
        
        print(f"\n=== TDD実践サマリー: {concept} ===")
        print(f"総実践回数: {summary['total_records']}")
        print(f"成功率: {summary['success_rate']:.1%}")
        
        print(f"\n📊 フェーズ別統計:")
        for phase, stats in summary["phases"].items():
            print(f"   {phase.upper()}: {stats['count']}回 (成功率: {stats['success_rate']:.1%})")
        
        # TDD実践度を表示
        concept_record = self.data_manager.get_concept_record(concept)
        if concept_record:
            print(f"\n🎯 現在のTDD実践度: {concept_record.tdd_proficiency.value}")

def main():
    if len(sys.argv) < 3:
        print("Usage: python tdd_tracker.py <phase> <concept> [test_file] [implementation_file] [notes]")
        print("Phases: red, green, refactor")
        sys.exit(1)
    
    phase_str = sys.argv[1].lower()
    concept = sys.argv[2]
    test_file = sys.argv[3] if len(sys.argv) > 3 else ""
    implementation_file = sys.argv[4] if len(sys.argv) > 4 else ""
    notes = sys.argv[5] if len(sys.argv) > 5 else ""
    
    try:
        phase = TDDPhase(phase_str)
    except ValueError:
        print(f"Invalid phase: {phase_str}. Use: red, green, refactor")
        sys.exit(1)
    
    tracker = TDDTracker()
    
    # 成功/失敗を確認
    success_input = input("実践は成功しましたか？ (y/n): ").lower()
    success = success_input in ['y', 'yes', '']
    
    error_message = None
    if not success:
        error_message = input("エラーメッセージを入力してください: ")
    
    # TDD実践を記録
    tracker.record_tdd_practice(
        concept=concept,
        phase=phase,
        test_file=test_file,
        implementation_file=implementation_file,
        success=success,
        error_message=error_message,
        notes=notes
    )
    
    # サマリーを表示
    tracker.display_tdd_summary(concept)

if __name__ == "__main__":
    main()
