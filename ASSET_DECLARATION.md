# 도빈(Dobin) 어셋 디클라인 (Asset Declaration)

## 프로젝트 정보
- **프로젝트명**: 도빈 (Dobin)
- **버전**: 1.0.0
- **유형**: 한글 기반 AI 코딩 어시스턴트
- **라이선스**: MIT License

## 아키텍처 선언

### 코어 모듈 (core/)
| 모듈 | 역할 | 의존성 |
|------|------|--------|
| `config.py` | 설정 관리 (모델, 작업디렉토리, 언어 등) | - |
| `agent.py` | Ollama 모델과의 통신 및 도구 호출 루프 | ollama, tools, memory, display |
| `tools.py` | 9가지 도구 정의 및 실행기 | subprocess, os, glob, re |
| `memory.py` | dobin.md 작업 기록 관리 | os, datetime |
| `display.py` | Rich 기반 한글 UI 렌더링 | rich |

### 진입점
| 파일 | 역할 |
|------|------|
| `app.py` | CLI 시작점, 인자 파싱, 에이전트 초기화 |

## 도구 선언 (Tool Assets)

| 도구 | 기능 | 입력 | 출력 |
|------|------|------|-------|
| `bash` | 셸 명령어 실행 | command, workdir, timeout | 명령어 stdout/stderr |
| `read_file` | 파일 읽기 | path, offset, limit | 줄 번호가 있는 파일 내용 |
| `write_file` | 파일 작성 | path, content | 작성 완료 메시지 |
| `edit_file` | 파일 부분 편집 | path, old_string, new_string, replace_all | 편집 결과 메시지 |
| `list_dir` | 디렉토리 나열 | path, recursive | 파일/폴더 목록 |
| `glob_search` | 글로브 패턴 파일 검색 | pattern, path | 매칭 파일 목록 |
| `grep_search` | 정규식 내용 검색 | pattern, path, include | 매칭 줄 목록 |
| `create_directory` | 디렉토리 생성 | path | 생성 완료 메시지 |
| `delete_path` | 파일/디렉토리 삭제 | path | 삭제 완료 메시지 |

## 데이터 어셋

### dobin.md (작업 기록)
- **위치**: 작업 디렉토리 루트에 자동 생성
- **구조**: 마크다운 형식, 사용자 요청/도구 호출/응답 자동 기록
- **목적**: 작업 이력 관리 및 컨텍스트 유지

### ~/.dobin_config.json (사용자 설정)
- **위치**: 홈 디렉토리
- **내용**: 모델명, 작업디렉토리, 최대반복수, 언어 설정

## 모델 의존성
- **런타임**: Ollama (https://ollama.com)
- **기본 모델**: kimi-k2.5:cloud
- **선택 가능 모델**:
  1. kimi-k2.5:cloud (기본)
  2. glm-5.1:cloud
  3. glm-4:cloud
  4. qwen3:cloud
  5. devstral:cloud
- **도구 호출**: Ollama 네이티브 tool calling 지원 필요

## 외부 의존성
| 패키지 | 버전 | 용도 |
|--------|------|-------|
| `ollama` | >=0.6.0 | Ollama API 클라이언트 |
| `rich` | >=13.0 | 터미널 UI 렌더링 |
| Python | >=3.9 | 런타임 |

## 기능 선언

1. **인터랙티브 대화**: 한글 기반 대화형 CLI 인터페이스
2. **도구 호출 루프**: AI가 도구를 호출 → 결과 반환 → AI가 판단 후 다음 행동
3. **파일 시스템 조작**: 읽기, 쓰기, 편집, 검색, 삭제
4. **터미널 명령 실행**: 셸 명령어 실행 및 결과 반환
5. **작업 기록 관리**: dobin.md에 모든 대화/도구사용 자동 기록
6. **슬래시 명령어**: /help, /quit, /clear, /model, /history, /dir
7. **모델 선택**: 시작 시 모델 선택 메뉴 제공, `/model` 명령으로 런타임 교체 가능

## 보안 고지
- `.env`, 보안 키, 자격증명 파일 내용 읽기 차단은 시스템 프롬프트로 권고만 적용
- 삭제 명령은 되돌릴 수 없으므로 AI가 사전 확인 권고