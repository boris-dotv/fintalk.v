#!/usr/bin/env python3
"""
FinTalk.AI - 主入口
选择你想要的运行模式
"""

import os
import sys

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# Setup path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))


def print_banner():
    print("\n" + "🚀"*40)
    print(" "*15 + "FinTalk.AI - Enhanced Financial Assistant")
    print(" "*20 + "MCP Architecture + GitHub Integration")
    print("🚀"*40)


def print_menu():
    print("\n" + "="*80)
    print("  运行模式选择")
    print("="*80)
    print("\n  [1] 🚀 完整Demo (demos/demo_with_mcp.py)")
    print("      本地数据库 + MCP外部工具 + GitHub管理")
    print("\n  [2] 🧪 GitHub MCP测试 (tests/test_github_mcp.py)")
    print("      测试GitHub API集成功能")
    print("\n  [3] 💻 直接运行主程序")
    print("      enhanced_fintalk.py (无交互)")
    print("\n  [0] 🚪 退出")
    print("\n" + "="*80)
    print("\n请选择 [0-3]: ", end="")


def run_demo():
    """运行完整Demo"""
    print("\n🚀 启动完整Demo...")
    from demos.demo_with_mcp import demo_with_mcp
    demo_with_mcp()
    input("\n按 Enter 键继续...")


def run_test():
    """运行GitHub MCP测试"""
    print("\n🧪 启动GitHub MCP测试...")
    from tests.test_github_mcp import main
    main()


def run_main():
    """直接运行主程序"""
    print("\n💻 运行主程序...")
    from enhanced_fintalk import demo_enhanced
    demo_enhanced()


def main():
    print_banner()

    while True:
        print_menu()
        choice = input().strip()

        if choice == "1":
            run_demo()
            break
        elif choice == "2":
            run_test()
            break
        elif choice == "3":
            run_main()
            break
        elif choice == "0":
            print("\n👋 Goodbye!")
            break
        else:
            print(f"\n❌ 无效选择: {choice}，请重新输入")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
