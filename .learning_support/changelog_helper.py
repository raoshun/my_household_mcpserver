#!/usr/bin/env python3
"""
学習支援システム - Changelogヘルパーモジュール
"""

import os
import sys
import uuid
from datetime import datetime
from typing import Dict, List, Optional


class ChangelogHelper:
    """Changelogヘルパークラス"""

    def __init__(self, changelog_dir: str = "changelog.d"):
        self.changelog_dir = changelog_dir
        self.fragment_types = {
            "feature": "新機能",
            "bugfix": "バグ修正",
            "doc": "ドキュメント",
            "removal": "削除・非推奨",
            "misc": "その他"
        }
        # changelog.dディレクトリを作成
        os.makedirs(self.changelog_dir, exist_ok=True)

    def create_fragment(self, fragment_type: str, description: str, issue_number: Optional[int] = None) -> str:
        """変更フラグメントを作成"""
        if fragment_type not in self.fragment_types:
            raise ValueError(f"無効なフラグメントタイプ: {fragment_type}")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        fragment_id = str(uuid.uuid4())[:8]
        if issue_number:
            filename = f"{timestamp}_{fragment_id}_{issue_number}.{fragment_type}.md"
        else:
            filename = f"{timestamp}_{fragment_id}.{fragment_type}.md"
        filepath = os.path.join(self.changelog_dir, filename)
        content = self._create_fragment_content(description, fragment_type, issue_number)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"✅ 変更フラグメントを作成しました: {filename}")
        print(f"   タイプ: {self.fragment_types[fragment_type]}")
        print(f"   説明: {description}")
        return filepath

    def _create_fragment_content(self, description: str, fragment_type: str, issue_number: Optional[int] = None) -> str:
        """フラグメント内容を作成"""
        content = description
        if issue_number:
            content += f" (#{issue_number})"
        return content

    def list_fragments(self) -> Dict[str, List[Dict[str, str]]]:
        """既存のフラグメントを一覧表示"""
        fragments: Dict[str, List[Dict[str, str]]] = {ftype: [] for ftype in self.fragment_types}
        if not os.path.exists(self.changelog_dir):
            return fragments
        for filename in os.listdir(self.changelog_dir):
            if filename.endswith('.md'):
                for ftype in self.fragment_types:
                    if f".{ftype}." in filename:
                        with open(os.path.join(self.changelog_dir, filename), 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                        fragments[ftype].append({
                            "filename": filename,
                            "content": content
                        })
                        break
        return fragments

    def display_fragments(self):
        """フラグメントを表示"""
        fragments = self.list_fragments()
        print("\n=== 変更フラグメント一覧 ===")
        total_count = sum(len(items) for items in fragments.values())
        if total_count == 0:
            print("📝 変更フラグメントはありません")
            return
        for ftype, items in fragments.items():
            if items:
                print(f"\n📋 {self.fragment_types[ftype]} ({len(items)}件):")
                for item in items:
                    print(f"   • {item['content']}")
                    print(f"     ({item['filename']})")
        print(f"\n📊 合計: {total_count}件の変更フラグメント")

    def validate_fragments(self) -> bool:
        """フラグメントの妥当性をチェック"""
        fragments = self.list_fragments()
        issues = []
        for items in fragments.values():
            for item in items:
                if not item['content'].strip():
                    issues.append(f"空の内容: {item['filename']}")
                elif len(item['content']) < 10:
                    issues.append(f"説明が短すぎます: {item['filename']}")
        if issues:
            print("\n❌ フラグメントの問題:")
            for issue in issues:
                print(f"   • {issue}")
            return False
        print("\n✅ すべてのフラグメントが妥当です")
        return True

    def suggest_version_bump(self) -> str:
        """バージョンアップの種類を提案"""
        fragments = self.list_fragments()
        if fragments["removal"]:
            return "major"  # 破壊的変更
        elif fragments["feature"]:
            return "minor"  # 機能追加
        elif fragments["bugfix"]:
            return "patch"  # バグ修正
        else:
            return "patch"  # その他

    def create_template_fragments(self):
        """テンプレートフラグメントを作成"""
        templates = {
            "feature": "新機能の説明をここに記入",
            "bugfix": "修正したバグの説明をここに記入",
            "doc": "ドキュメントの変更内容をここに記入",
            "removal": "削除・非推奨の内容をここに記入",
            "misc": "その他の変更内容をここに記入"
        }
        print("\n=== テンプレートフラグメント作成 ===")
        for ftype, template in templates.items():
            filename = f"template.{ftype}.md"
            filepath = os.path.join(self.changelog_dir, filename)
            if not os.path.exists(filepath):
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(template)
                print(f"✅ テンプレート作成: {filename}")
            else:
                print(f"⚠️  テンプレート既存: {filename}")

    def auto_create_fragment(self, git_message: str) -> Optional[str]:
        """Gitメッセージから自動的にフラグメントを作成"""
        message_lower = git_message.lower()
        fragment_type = None
        if any(keyword in message_lower for keyword in ['add', 'feat', 'feature', '追加', '新機能']):
            fragment_type = "feature"
        elif any(keyword in message_lower for keyword in ['fix', 'bug', 'bugfix', '修正', 'バグ']):
            fragment_type = "bugfix"
        elif any(keyword in message_lower for keyword in ['doc', 'docs', 'document', 'ドキュメント']):
            fragment_type = "doc"
        elif any(keyword in message_lower for keyword in ['remove', 'delete', 'deprecate', '削除', '非推奨']):
            fragment_type = "removal"
        else:
            fragment_type = "misc"
        if fragment_type:
            return self.create_fragment(fragment_type, git_message)
        return None

    def get_current_version(self, pyproject_path: str = "pyproject.toml") -> str:
        """pyproject.tomlから現在のバージョンを取得"""
        if not os.path.exists(pyproject_path):
            return "0.0.0"
        with open(pyproject_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith("version"):
                    return line.split('=')[1].strip().replace('"', '').replace("'", '')
        return "0.0.0"

    def bump_version(self, current_version: str, bump_type: str) -> str:
        """バージョン番号を種別に応じてインクリメント"""
        major, minor, patch = [int(x) for x in current_version.split('.')]
        if bump_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif bump_type == "minor":
            minor += 1
            patch = 0
        else:
            patch += 1
        return f"{major}.{minor}.{patch}"

    def update_pyproject_version(self, new_version: str, pyproject_path: str = "pyproject.toml"):
        """pyproject.tomlのバージョン番号を自動更新（雛形）"""
        if not os.path.exists(pyproject_path):
            print(f"⚠️ {pyproject_path}が見つかりません")
            return
        lines = []
        with open(pyproject_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith("version"):
                    lines.append(f'version = "{new_version}"\n')
                else:
                    lines.append(line)
        with open(pyproject_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"✅ pyproject.tomlのバージョンを{new_version}に更新しました")


def main():
    """コマンドラインエントリポイント"""
    if len(sys.argv) < 2:
        print("Usage: python changelog_helper.py <command> [args...]")
        print("Commands:")
        print("  create <type> <description> [issue_number]")
        print("  list")
        print("  validate")
        print("  suggest")
        print("  template")
        print("  auto <git_message>")
        sys.exit(1)
    helper = ChangelogHelper()
    command = sys.argv[1]
    if command == "create":
        if len(sys.argv) < 4:
            print("Usage: python changelog_helper.py create <type> <description> [issue_number]")
            print("Types: feature, bugfix, doc, removal, misc")
            sys.exit(1)
        fragment_type = sys.argv[2]
        description = sys.argv[3]
        issue_number = int(sys.argv[4]) if len(sys.argv) > 4 else None
        try:
            helper.create_fragment(fragment_type, description, issue_number)
        except ValueError as e:
            print(f"❌ エラー: {e}")
    elif command == "list":
        helper.display_fragments()
    elif command == "validate":
        helper.validate_fragments()
    elif command == "suggest":
        version_bump = helper.suggest_version_bump()
        current_version = helper.get_current_version()
        next_version = helper.bump_version(current_version, version_bump)
        print(f"\n💡 推奨バージョンアップ: {version_bump}")
        print(f"   現在のバージョン: {current_version}")
        print(f"   次のバージョン: {next_version}")
        # 自動更新例: helper.update_pyproject_version(next_version)
    elif command == "template":
        helper.create_template_fragments()
    elif command == "auto":
        if len(sys.argv) < 3:
            print("Usage: python changelog_helper.py auto <git_message>")
            sys.exit(1)
        git_message = sys.argv[2]
        result = helper.auto_create_fragment(git_message)
        if result:
            print(f"✅ 自動作成成功: {result}")
        else:
            print("❌ 自動作成に失敗しました")
    else:
        print(f"❌ 不明なコマンド: {command}")


if __name__ == "__main__":
    main()
