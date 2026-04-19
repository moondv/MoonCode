import os
import datetime
import re
from typing import List, Dict, Optional

class ImportantTask:
    """중요 요청을 표현하는 클래스"""
    def __init__(self, title: str, content: str, category: str = "기타", tags: List[str] = None):
        self.id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.title = title
        self.content = content
        self.category = category  # 디자인, 기능추가, 버그수정, 리팩토링, 기타
        self.tags = tags or []
        self.status = "진행중"  # 진행중, 완료, 보류
        self.related_files = []

    def to_markdown(self) -> str:
        tags_str = " ".join([f"`#{t}`" for t in self.tags]) if self.tags else ""
        return f"""### 📌 {self.title}

**ID**: `{self.id}` | **시간**: {self.timestamp} | **분류**: `{self.category}` | **상태**: `{self.status}`

{tags_str}

**요청 내용**:
> {self.content}

**관련 파일**:
{chr(10).join([f'- `{f}`' for f in self.related_files]) if self.related_files else '- 없음'}

---

"""


class DobinMemory:
    """도빈의 메모리 관리 시스템"""
    
    def __init__(self, workdir: str):
        self.workdir = workdir
        self.dobin_folder = os.path.join(workdir, "dobin_code")
        self.md_path = os.path.join(self.dobin_folder, "dobin.md")
        self.project_path = os.path.join(self.dobin_folder, "project.md")
        
        # 중요 요청 메모리 (인메모리 캐시)
        self.important_tasks: List[ImportantTask] = []
        
        self._ensure_structure()
        self._load_existing_tasks()

    def _ensure_structure(self):
        """dobin_code 폴더와 기본 파일들 생성"""
        os.makedirs(self.dobin_folder, exist_ok=True)
        
        # dobin.md - 중요 요청 기록
        if not os.path.exists(self.md_path):
            with open(self.md_path, "w", encoding="utf-8") as f:
                f.write(self._generate_dobin_header())
        
        # project.md - 프로젝트 문서
        if not os.path.exists(self.project_path):
            with open(self.project_path, "w", encoding="utf-8") as f:
                f.write(self._generate_project_header())

    def _generate_dobin_header(self) -> str:
        """dobin.md 헤더 생성"""
        return f"""# 🤖 도빈 기억장치 (Dobin Memory)

> 자동 생성된 AI 기억 저장소
> 생성일: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📋 중요 요청 기록

중요한 사용자 요청들이 여기에 기록됩니다.
- **디자인 요청**: UI/UX 개선, 색상 변경 등
- **기능 추가**: 새로운 기능 구현
- **버그 수정**: 오류 수정 요청
- **리팩토링**: 코드 구조 개선

---

"""

    def _generate_project_header(self) -> str:
        """project.md 헤더 생성"""
        return f"""# 📁 프로젝트 문서

> 자동 생성된 프로젝트 개요
> 마지막 업데이트: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 🏗️ 프로젝트 구조

```
{self._get_directory_tree()}
```

## 📝 최근 변경사항

- {datetime.datetime.now().strftime('%Y-%m-%d')}: 프로젝트 문서 생성

---

## 🎯 주요 목표

*아직 설정된 목표가 없습니다.*

## 📚 참고 문서

- `dobin_code/dobin.md` - AI 기억장치
- `dobin_code/project.md` - 이 문서

---

"""

    def _get_directory_tree(self, max_depth: int = 3) -> str:
        """디렉토리 트리 생성"""
        lines = [f"{os.path.basename(self.workdir)}/"]
        try:
            for item in sorted(os.listdir(self.workdir)):
                if item.startswith('.') or item == "__pycache__":
                    continue
                if item == "dobin_code":
                    lines.append(f"├── {item}/")
                    lines.append(f"│   ├── dobin.md")
                    lines.append(f"│   └── project.md")
                elif os.path.isdir(os.path.join(self.workdir, item)):
                    lines.append(f"├── {item}/")
                else:
                    lines.append(f"├── {item}")
        except Exception:
            lines.append("(디렉토리 읽기 실패)")
        return "\n".join(lines)

    def _load_existing_tasks(self):
        """기존 dobin.md에서 중요 요청 로드"""
        if not os.path.exists(self.md_path):
            return
        try:
            with open(self.md_path, "r", encoding="utf-8") as f:
                content = f.read()
            # 간단한 파싱 (실제로는 더 정교하게 할 수 있음)
        except Exception:
            pass

    def _analyze_importance(self, user_input: str) -> tuple[bool, str, str, List[str]]:
        """
        요청의 중요도 분석
        Returns: (is_important, category, title, tags)
        """
        input_lower = user_input.lower()
        
        # 디자인 요청
        design_keywords = ["디자인", "ui", "ux", "화면", "색상", "스타일", "배너", "로고", "폰트", "레이아웃", "버튼", "카드", "입체", "그라데이션", "네온", "어두운"]
        
        # 기능 추가
        feature_keywords = ["추가", "만들어", "생성", "구현", "기능", "새로운", "추가해", "만들게"]
        
        # 버그 수정
        bug_keywords = ["버그", "오류", "수정", "고쳐", "안 돼", "실패", "에러"]
        
        # 리팩토링
        refactor_keywords = ["리팩토링", "구조", "개선", "정리", "분리", "모듈화"]
        
        tags = []
        is_important = False
        category = "기타"
        title = user_input[:30] + "..." if len(user_input) > 30 else user_input
        
        # 디자인 요청 확인
        if any(kw in input_lower for kw in design_keywords):
            is_important = True
            category = "디자인"
            tags.append("UI/UX")
            if "디자인" in input_lower:
                title = re.sub(r".*디자인\s*", "디자인: ", user_input)[:40]
        
        # 기능 추가 확인
        elif any(kw in input_lower for kw in feature_keywords):
            is_important = True
            category = "기능추가"
            tags.append("feature")
        
        # 버그 수정 확인
        elif any(kw in input_lower for kw in bug_keywords):
            is_important = True
            category = "버그수정"
            tags.append("bugfix")
        
        # 리팩토링 확인
        elif any(kw in input_lower for kw in refactor_keywords):
            is_important = True
            category = "리팩토링"
            tags.append("refactor")
        
        return is_important, category, title, tags

    def log_request(self, user_input: str):
        """사용자 요청을 기록하고 중요한 경우 dobin.md에 저장"""
        # 일단 프로젝트.md에 기록
        self._log_to_project("user_request", user_input)
        
        # 중요도 분석
        is_important, category, title, tags = self._analyze_importance(user_input)
        
        if is_important:
            task = ImportantTask(
                title=title,
                content=user_input,
                category=category,
                tags=tags
            )
            self.important_tasks.append(task)
            self._save_important_task(task)
            return True, task
        return False, None

    def _save_important_task(self, task: ImportantTask):
        """중요 요청을 dobin.md에 저장"""
        with open(self.md_path, "a", encoding="utf-8") as f:
            f.write(task.to_markdown())

    def _log_to_project(self, log_type: str, content: str):
        """project.md에 로그 추가 (최근 변경사항 섹션)"""
        ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        # 실제 구현에서는 섹션을 파싱해서 업데이트하는 로직 필요
        # 여기서는 간단하게 append만
        pass

    def log_response(self, response_text: str):
        """AI 응답 기록"""
        # 응답은 너무 많아지지 않도록 프로젝트.md에 간략히만
        pass

    def log_tool(self, tool_name: str, args: str, result_summary: str):
        """도구 호출 기록"""
        ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # 현재 진행 중인 태스크에 관련 파일 추가
        if self.important_tasks and self.important_tasks[-1].status == "진행중":
            # 파일 관련 도구인 경우
            if tool_name in ["write_file", "edit_file", "read_file"]:
                try:
                    import json
                    args_dict = json.loads(args) if isinstance(args, str) else args
                    path = args_dict.get("path", "")
                    if path and path not in self.important_tasks[-1].related_files:
                        self.important_tasks[-1].related_files.append(path)
                except:
                    pass

    def update_task_status(self, task_id: str, status: str):
        """태스크 상태 업데이트"""
        for task in self.important_tasks:
            if task.id == task_id:
                task.status = status
                break

    def get_important_tasks(self, category: Optional[str] = None, status: Optional[str] = None) -> List[ImportantTask]:
        """중요 요청 조회"""
        filtered = self.important_tasks
        if category:
            filtered = [t for t in filtered if t.category == category]
        if status:
            filtered = [t for t in filtered if t.status == status]
        return filtered

    def get_task_summary(self) -> str:
        """태스크 요약 반환"""
        if not self.important_tasks:
            return "중요 요청 없음"
        
        lines = [f"📝 중요 요청 {len(self.important_tasks)}개 기록됨:"]
        for t in self.important_tasks[-5:]:  # 최근 5개
            lines.append(f"  • [{t.category}] {t.title} ({t.status})")
        return "\n".join(lines)

    def update_docs(self, section_title: str, content: str):
        """project.md에 문서 섹션 추가"""
        ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(self.project_path, "a", encoding="utf-8") as f:
            f.write(f"\n## {section_title} [{ts}]\n\n{content}\n\n")

    def read(self) -> str:
        """dobin.md 읽기"""
        if os.path.exists(self.md_path):
            with open(self.md_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def read_project(self) -> str:
        """project.md 읽기"""
        if os.path.exists(self.project_path):
            with open(self.project_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def get_recent_context(self, max_lines: int = 50) -> str:
        """최근 컨텍스트 반환"""
        content = self.read()
        lines = content.split("\n")
        return "\n".join(lines[-max_lines:])