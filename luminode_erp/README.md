# Luminode ERP 설계·구현계획 패키지

이 폴더는 회사 자체 서버에 구축할 Luminode ERP Platform의 승인된 상세설계와 에이전트 병렬 개발용 구현 계획을 함께 제공한다.

## 먼저 읽을 문서

- 한 파일로 보려면 `LUMINODE_ERP_APPROVED_DESIGN_AND_IMPLEMENTATION.md`

1. `APPROVAL_RECORD.md`
2. `00_MASTER_DESIGN.md`
3. `14_MASTER_IMPLEMENTATION_PLAN.md`
4. `15_PHASE_0_FOUNDATION_IMPLEMENTATION_PLAN.md`
5. `16_AGENT_ORCHESTRATION_RUNBOOK.md`
6. `AGENTS.md`
7. `work_packages.yaml`

## 실제 에이전트 실행에 사용하는 파일

- `17_PHASE_0_AGENT_PROMPTS.md`: Coordinator, Architect, QA, Phase 0 작업별 확정 프롬프트
- `agent_execution_plan.yaml`: Phase 0~7 실행 파동과 역할·브랜치·게이트
- `IMPLEMENTATION_PLAN_REVIEW.md`: dependency·문서·범위 자체 검토 결과
- `phase0_issue_board.csv`: Phase 0 작업 보드 초기 데이터
- `work_packages/`: 71개 작업 패키지의 개별 Markdown
- `13_AGENT_PROMPT_TEMPLATES.md`: Phase 1 이후 재사용할 역할별 공통 프롬프트
- `DECISIONS.md`: 승인된 ADR 기준선

## 문서 구성

| 파일 | 용도 |
|---|---|
| `00_MASTER_DESIGN.md` | 목표·범위·원칙·상위 구조 |
| `01_PRODUCT_REQUIREMENTS.md` | 제품 요구사항과 사용자 여정 |
| `02_SYSTEM_ARCHITECTURE.md` | 애플리케이션·트랜잭션·파일·검색 구조 |
| `03_MODULE_SPECIFICATIONS.md` | ERP 전체 모듈 기능 |
| `04_DATA_MODEL.md` | 테이블·관계·제약·보존 |
| `05_API_AND_EVENT_CONTRACTS.md` | REST·이벤트·AI Tool 계약 |
| `06_UI_UX_INFORMATION_ARCHITECTURE.md` | 메뉴·화면·상태·접근성 |
| `07_AI_AGENT_ARCHITECTURE.md` | RAG·오케스트레이터·에이전트 안전성 |
| `08_SECURITY_AND_GOVERNANCE.md` | 인증·권한·감사·개인정보 |
| `09_INFRASTRUCTURE_AND_OPERATIONS.md` | 자체 서버·배포·백업·복구 |
| `10_TEST_AND_QUALITY.md` | 테스트와 릴리스 게이트 |
| `11_DELIVERY_ROADMAP.md` | Phase 0~7 로드맵 |
| `12_AGENT_WORKING_RULES.md` | 개발 에이전트 공통 규칙 |
| `14_MASTER_IMPLEMENTATION_PLAN.md` | 전체 구현 실행 계획 |
| `15_PHASE_0_FOUNDATION_IMPLEMENTATION_PLAN.md` | 첫 단계 파일별 구현 계획 |
| `16_AGENT_ORCHESTRATION_RUNBOOK.md` | worktree·MR·리뷰·충돌 통제 |
| `17_PHASE_0_AGENT_PROMPTS.md` | 그대로 전달 가능한 에이전트 프롬프트 |

## 권장 시작

1. 새 Git 저장소를 만든다.
2. 이 패키지를 `docs/specs`와 `docs/work-packages`에 배치한다.
3. 루트에 `AGENTS.md`, `DECISIONS.md`를 복사한다.
4. Coordinator Agent에 `17_PHASE_0_AGENT_PROMPTS.md`의 시작 프롬프트를 전달한다.
5. 첫 구현 작업은 반드시 `WP-PLT-001`로 시작한다.
6. `WP-QA-000`을 통과하기 전 Phase 1 기능을 운영 브랜치에 병합하지 않는다.
