import os
import subprocess
import json
import fnmatch
import shutil
import re
from collections import deque

# 직전 파일 상태 스택 (undo용). 최대 20개까지 보관.
_EDIT_HISTORY = deque(maxlen=20)


def _snapshot_before_edit(path):
    """편집 전 파일 스냅샷 저장 (undo용)"""
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            _EDIT_HISTORY.append((path, content, True))
        else:
            _EDIT_HISTORY.append((path, None, False))  # 원래 없던 파일
    except Exception:
        pass

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "터미널에서 셸 명령어를 실행합니다. 명령어 출력을 반환합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "실행할 셸 명령어"
                    },
                    "workdir": {
                        "type": "string",
                        "description": "작업 디렉토리 (기본값: 현재 디렉토리)"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "타임아웃 (초, 기본값: 120)"
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "파일의 내용을 읽습니다. 특정 줄 범위도 읽을 수 있습니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "읽을 파일 경로"
                    },
                    "offset": {
                        "type": "integer",
                        "description": "시작 줄 번호 (1부터, 기본값: 1)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "읽을 최대 줄 수 (기본값: 2000)"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "파일에 내용을 씁니다. 파일이 없으면 생성합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "쓸 파일 경로"
                    },
                    "content": {
                        "type": "string",
                        "description": "파일에 쓸 내용"
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "파일의 특정 문자열을 찾아서 다른 문자열로 교체합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "편집할 파일 경로"
                    },
                    "old_string": {
                        "type": "string",
                        "description": "찾을 문자열"
                    },
                    "new_string": {
                        "type": "string",
                        "description": "교체할 새 문자열"
                    },
                    "replace_all": {
                        "type": "boolean",
                        "description": "모든 일치 항목 교체 여부 (기본값: false)"
                    }
                },
                "required": ["path", "old_string", "new_string"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "디렉토리의 파일과 폴더를 나열합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "디렉토리 경로 (기본값: 현재 디렉토리)"
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "하위 디렉토리까지 재귀적으로 나열할지 여부"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "glob_search",
            "description": "글로브 패턴으로 파일을 검색합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "글로브 패턴 (예: **/*.py)"
                    },
                    "path": {
                        "type": "string",
                        "description": "검색할 디렉토리 경로"
                    }
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "grep_search",
            "description": "정규식 패턴으로 파일 내용을 검색합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "검색할 정규식 패턴"
                    },
                    "path": {
                        "type": "string",
                        "description": "검색할 디렉토리 경로"
                    },
                    "include": {
                        "type": "string",
                        "description": "포함할 파일 패턴 (예: *.py)"
                    }
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_directory",
            "description": "새 디렉토리를 생성합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "생성할 디렉토리 경로"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_path",
            "description": "파일이나 디렉토리를 삭제합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "삭제할 파일/디렉토리 경로"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_symbols",
            "description": "코드베이스에서 함수/클래스/변수 정의를 찾습니다. Python, JS/TS, Go 등 지원. 심볼 이름으로 즉시 정의 위치를 찾을 때 사용하세요.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "찾을 심볼 이름 (예: 'processData', 'UserService')"
                    },
                    "path": {
                        "type": "string",
                        "description": "검색할 디렉토리 (기본값: 작업 디렉토리)"
                    },
                    "kind": {
                        "type": "string",
                        "description": "심볼 종류: 'function' | 'class' | 'any' (기본값: 'any')"
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "replace_lines",
            "description": "파일의 특정 줄 범위를 새 내용으로 교체합니다. edit_file보다 정밀하게 줄 단위 수정할 때 사용하세요. 줄 번호는 1부터 시작.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "수정할 파일 경로"
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "교체 시작 줄 번호 (1부터)"
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "교체 끝 줄 번호 (포함)"
                    },
                    "new_content": {
                        "type": "string",
                        "description": "해당 줄을 대체할 새 내용 (줄바꿈 포함 가능)"
                    }
                },
                "required": ["path", "start_line", "end_line", "new_content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "undo",
            "description": "직전 파일 수정(write_file / edit_file / replace_lines / delete_path)을 되돌립니다.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_status",
            "description": "Git 저장소의 상태를 확인합니다. 변경된 파일, 스테이징된 파일, 브랜치 정보를 보여줍니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Git 저장소 경로 (기본값: 작업 디렉토리)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_commit",
            "description": "변경사항을 커밋합니다. 지정된 파일들을 스테이징하고 메시지와 함께 커밋합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "커밋 메시지"
                    },
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "스테이징할 파일 목록 (생략하면 변경된 모든 추적 파일)"
                    }
                },
                "required": ["message"]
            }
        }
    },
]


def execute_tool(tool_name, args, workdir=None):
    cwd = args.get("workdir", workdir) if workdir else workdir

    if tool_name == "bash":
        command = args["command"]
        timeout = args.get("timeout", 120)
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True,
                timeout=timeout, cwd=cwd
            )
            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                output += "\n[STDERR]\n" + result.stderr
            if result.returncode != 0:
                output += f"\n[종료 코드: {result.returncode}]"
            return output.strip() if output.strip() else "(출력 없음)"
        except subprocess.TimeoutExpired:
            return f"오류: 명령어가 {timeout}초 내에 완료되지 않았습니다."
        except Exception as e:
            return f"오류: {str(e)}"

    elif tool_name == "read_file":
        path = args["path"]
        if not os.path.isabs(path):
            path = os.path.join(cwd or os.getcwd(), path)
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            offset = args.get("offset", 1) - 1
            limit = args.get("limit", 2000)
            selected = lines[offset:offset + limit]
            numbered = []
            for i, line in enumerate(selected, start=offset + 1):
                numbered.append(f"{i}: {line.rstrip()}")
            return "\n".join(numbered) if numbered else "(빈 파일)"
        except FileNotFoundError:
            return f"오류: 파일을 찾을 수 없습니다 - {path}"
        except Exception as e:
            return f"오류: {str(e)}"

    elif tool_name == "write_file":
        path = args["path"]
        if not os.path.isabs(path):
            path = os.path.join(cwd or os.getcwd(), path)
        try:
            _snapshot_before_edit(path)
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(args["content"])
            return f"파일 작성 완료: {path}"
        except Exception as e:
            return f"오류: {str(e)}"

    elif tool_name == "edit_file":
        path = args["path"]
        if not os.path.isabs(path):
            path = os.path.join(cwd or os.getcwd(), path)
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            old = args["old_string"]
            new = args["new_string"]
            replace_all = args.get("replace_all", False)
            count = content.count(old)
            if count == 0:
                return f"오류: '{old}' 문자열을 찾을 수 없습니다."
            if count > 1 and not replace_all:
                return f"오류: '{old}' 문자열이 {count}개 발견되었습니다. replace_all=true로 설정하거나 더 구체적인 문자열을 사용하세요."
            _snapshot_before_edit(path)
            if replace_all:
                content = content.replace(old, new)
            else:
                content = content.replace(old, new, 1)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"파일 편집 완료: {path} ({count}개 항목 교체)"
        except FileNotFoundError:
            return f"오류: 파일을 찾을 수 없습니다 - {path}"
        except Exception as e:
            return f"오류: {str(e)}"

    elif tool_name == "list_dir":
        path = args.get("path", ".")
        if not os.path.isabs(path):
            path = os.path.join(cwd or os.getcwd(), path)
        recursive = args.get("recursive", False)
        try:
            entries = []
            if recursive:
                for root, dirs, files in os.walk(path):
                    level = root.replace(path, "").count(os.sep)
                    indent = "  " * level
                    entries.append(f"{indent}{os.path.basename(root)}/")
                    subindent = "  " * (level + 1)
                    for file in files:
                        entries.append(f"{subindent}{file}")
            else:
                for entry in sorted(os.listdir(path)):
                    full = os.path.join(path, entry)
                    if os.path.isdir(full):
                        entries.append(f"{entry}/")
                    else:
                        entries.append(entry)
            return "\n".join(entries) if entries else "(빈 디렉토리)"
        except FileNotFoundError:
            return f"오류: 디렉토리를 찾을 수 없습니다 - {path}"
        except Exception as e:
            return f"오류: {str(e)}"

    elif tool_name == "glob_search":
        pattern = args["pattern"]
        path = args.get("path", cwd or os.getcwd())
        try:
            import glob as globmod
            matches = globmod.glob(os.path.join(path, pattern), recursive=True)
            if matches:
                return "\n".join(matches)
            return "검색 결과가 없습니다."
        except Exception as e:
            return f"오류: {str(e)}"

    elif tool_name == "grep_search":
        pattern = args["pattern"]
        path = args.get("path", cwd or os.getcwd())
        include = args.get("include", "")
        try:
            cmd = ["grep", "-rn", "-E", pattern, path]
            if include:
                cmd.extend(["--include", include])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.stdout:
                lines = result.stdout.strip().split("\n")
                if len(lines) > 100:
                    return "\n".join(lines[:100]) + f"\n... 외 {len(lines)-100}개 결과"
                return "\n".join(lines)
            return "검색 결과가 없습니다."
        except subprocess.TimeoutExpired:
            return "오류: 검색 시간이 초과되었습니다."
        except Exception as e:
            try:
                results = []
                for root, dirs, files in os.walk(path):
                    for fname in files:
                        fpath = os.path.join(root, fname)
                        if include and not fnmatch.fnmatch(fname, include):
                            continue
                        try:
                            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                                for i, line in enumerate(f, 1):
                                    if re.search(pattern, line):
                                        results.append(f"{fpath}:{i}: {line.rstrip()}")
                                        if len(results) > 100:
                                            return "\n".join(results) + "\n... 결과가 너무 많습니다."
                        except:
                            pass
                return "\n".join(results) if results else "검색 결과가 없습니다."
            except Exception as e2:
                return f"오류: {str(e2)}"

    elif tool_name == "create_directory":
        path = args["path"]
        if not os.path.isabs(path):
            path = os.path.join(cwd or os.getcwd(), path)
        try:
            os.makedirs(path, exist_ok=True)
            return f"디렉토리 생성 완료: {path}"
        except Exception as e:
            return f"오류: {str(e)}"

    elif tool_name == "delete_path":
        path = args["path"]
        if not os.path.isabs(path):
            path = os.path.join(cwd or os.getcwd(), path)
        try:
            if os.path.isdir(path):
                # 디렉토리는 undo 지원 안 함 — 안전상 경고
                shutil.rmtree(path)
                return f"디렉토리 삭제 완료: {path} (undo 불가)"
            else:
                _snapshot_before_edit(path)
                os.remove(path)
                return f"삭제 완료: {path}"
        except FileNotFoundError:
            return f"오류: 경로를 찾을 수 없습니다 - {path}"
        except Exception as e:
            return f"오류: {str(e)}"

    elif tool_name == "search_symbols":
        name = args["name"]
        path = args.get("path", cwd or os.getcwd())
        kind = args.get("kind", "any")
        try:
            patterns = []
            # Python
            if kind in ("any", "function"):
                patterns.append(rf"^\s*def\s+{re.escape(name)}\s*\(")
                patterns.append(rf"^\s*async\s+def\s+{re.escape(name)}\s*\(")
            if kind in ("any", "class"):
                patterns.append(rf"^\s*class\s+{re.escape(name)}\s*[\(:]")
            # JS/TS
            if kind in ("any", "function"):
                patterns.append(rf"function\s+{re.escape(name)}\s*\(")
                patterns.append(rf"(?:const|let|var)\s+{re.escape(name)}\s*=\s*(?:async\s*)?\(")
                patterns.append(rf"{re.escape(name)}\s*:\s*(?:async\s*)?function")
                patterns.append(rf"{re.escape(name)}\s*\([^)]*\)\s*(?::\s*[^={{]+)?\s*{{")
            if kind in ("any", "class"):
                patterns.append(rf"class\s+{re.escape(name)}\s*[\{{extends]")
            # Go
            if kind in ("any", "function"):
                patterns.append(rf"func\s+(?:\([^)]+\)\s+)?{re.escape(name)}\s*\(")
            if kind in ("any", "class"):
                patterns.append(rf"type\s+{re.escape(name)}\s+(?:struct|interface)")

            big_pattern = "|".join(f"({p})" for p in patterns)
            results = []
            exts = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".kt", ".swift", ".rb", ".php", ".c", ".cpp", ".h", ".hpp"}
            for root, dirs, files in os.walk(path):
                # 흔한 무시 디렉토리
                dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".next")]
                for fname in files:
                    if os.path.splitext(fname)[1].lower() not in exts:
                        continue
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            for i, line in enumerate(f, 1):
                                if re.search(big_pattern, line):
                                    rel = os.path.relpath(fpath, path)
                                    results.append(f"{rel}:{i}: {line.rstrip()}")
                                    if len(results) >= 50:
                                        return "\n".join(results) + "\n(50개 이상 결과 — 일부만 표시)"
                    except Exception:
                        continue
            if not results:
                return f"심볼 '{name}' 정의를 찾을 수 없습니다."
            return "\n".join(results)
        except Exception as e:
            return f"오류: {str(e)}"

    elif tool_name == "replace_lines":
        path = args["path"]
        if not os.path.isabs(path):
            path = os.path.join(cwd or os.getcwd(), path)
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            start = args["start_line"]
            end = args["end_line"]
            if start < 1 or end > len(lines) or start > end:
                return f"오류: 잘못된 줄 범위 ({start}-{end}). 파일 길이: {len(lines)}줄"
            _snapshot_before_edit(path)
            new_content = args["new_content"]
            if new_content and not new_content.endswith("\n"):
                new_content += "\n"
            new_lines = lines[:start - 1] + [new_content] + lines[end:]
            # new_content 내부에 줄바꿈이 있으면 단일 문자열로 붙어있는데 join 시 괜찮음
            with open(path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            replaced_count = end - start + 1
            return f"줄 교체 완료: {path} ({start}-{end}행, {replaced_count}줄 → 새 내용)"
        except FileNotFoundError:
            return f"오류: 파일을 찾을 수 없습니다 - {path}"
        except Exception as e:
            return f"오류: {str(e)}"

    elif tool_name == "undo":
        if not _EDIT_HISTORY:
            return "되돌릴 수정 내역이 없습니다."
        path, content, existed = _EDIT_HISTORY.pop()
        try:
            if existed:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                return f"되돌림 완료: {path} (이전 상태로 복원)"
            else:
                # 원래 없던 파일이라면 삭제
                if os.path.exists(path):
                    os.remove(path)
                return f"되돌림 완료: {path} (원래 없던 파일이라 삭제)"
        except Exception as e:
            return f"오류: 되돌리기 실패 - {str(e)}"

    elif tool_name == "git_status":
        repo = args.get("path", cwd or os.getcwd())
        try:
            result = subprocess.run(
                ["git", "status", "--short", "--branch"],
                cwd=repo, capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                err = result.stderr.strip()
                if "not a git repository" in err.lower():
                    return "Git 저장소가 아닙니다."
                return f"오류: {err}"
            output = result.stdout.strip()
            return output if output else "깨끗한 작업 트리입니다 (변경 없음)"
        except FileNotFoundError:
            return "오류: git 명령을 찾을 수 없습니다."
        except Exception as e:
            return f"오류: {str(e)}"

    elif tool_name == "git_commit":
        repo = cwd or os.getcwd()
        message = args["message"]
        files = args.get("files")
        try:
            # 스테이징
            if files:
                stage_cmd = ["git", "add"] + files
            else:
                stage_cmd = ["git", "add", "-u"]  # 추적 중인 파일의 변경만
            stage = subprocess.run(stage_cmd, cwd=repo, capture_output=True, text=True, timeout=15)
            if stage.returncode != 0:
                return f"오류(git add): {stage.stderr.strip()}"

            # 스테이징된 변경 확인
            diff = subprocess.run(
                ["git", "diff", "--cached", "--stat"],
                cwd=repo, capture_output=True, text=True, timeout=10,
            )
            if not diff.stdout.strip():
                return "스테이징된 변경사항이 없어 커밋하지 않았습니다."

            commit = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=repo, capture_output=True, text=True, timeout=15,
            )
            if commit.returncode != 0:
                return f"오류(git commit): {commit.stderr.strip() or commit.stdout.strip()}"
            return f"커밋 완료:\n{commit.stdout.strip()}"
        except FileNotFoundError:
            return "오류: git 명령을 찾을 수 없습니다."
        except Exception as e:
            return f"오류: {str(e)}"

    else:
        return f"오류: 알 수 없는 도구 - {tool_name}"