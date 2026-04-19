#!/usr/bin/env python3
import os
import sys
from core.config import load_config
from core.agent import DobinAgent


def main():
    workdir = os.getcwd()

    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg in ["-h", "--help"]:
            print("DOBIN CODE — 한글 기반 AI 코딩 어시스턴트")
            print()
            print("사용법: dobin [작업디렉토리]")
            print()
            print("옵션:")
            print("  -h, --help    도움말 표시")
            print()
            print("작업 디렉토리를 지정하지 않으면 현재 디렉토리에서 시작합니다.")
            return
        elif os.path.isdir(arg):
            workdir = os.path.abspath(arg)
        else:
            print(f"오류: '{arg}' 디렉토리를 찾을 수 없습니다.")
            sys.exit(1)

    config = load_config()
    config["workdir"] = workdir

    agent = DobinAgent(config)
    agent.run_interactive()


if __name__ == "__main__":
    main()