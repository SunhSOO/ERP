# 구현계획 자체 검토 결과

- 검토일: 2026-08-05
- 검토 대상: 승인 설계, 마스터 구현계획, Phase 0 상세계획, 에이전트 운영서·프롬프트·실행 보드
- 결과: 구현계획 검토 가능 상태

## 1. 자동 검증

| 항목 | 결과 |
|---|---|
| 작업 패키지 수 | 71개 |
| 작업 패키지 ID 중복 | 0건 |
| 존재하지 않는 dependency | 0건 |
| dependency cycle | 0건 |
| Phase 0 작업 | 11개 |
| Phase 0 issue board 행 | 11개 |
| 개별 작업 패키지 문서 | 71개 |
| YAML 파싱 | `work_packages.yaml`, `agent_execution_plan.yaml` 모두 통과 |
| Markdown code fence 불균형 | 0건 |
| 신규 계획 문서의 TODO/TBD | 0건 |
| 승인 전 상태 문구 잔존 | 0건 |

## 2. 내부 일관성 검토

### 단계 순서

- 실행은 Phase 0~7의 **엄격한 단계 게이트**를 사용한다.
- 기존 dependency만 보면 앞당겨 시작할 수 있는 작업도 있지만, 안정된 공통 계약과 실제 사용자 검증을 위해 다음 Phase 병합은 이전 Phase 게이트 뒤로 제한했다.
- Phase별 파동 안에서는 dependency가 없는 작업만 병렬 배치했다.

### 인증과 RBAC의 초기화 순서

- `WP-PLT-002`에서 초기 관리자와 인증을 만든다.
- `WP-PLT-003`의 조직관리 기능은 RBAC 완성 전까지 feature flag와 일시적 bootstrap 관리자에게만 제한한다.
- `WP-PLT-004`에서 승인된 시스템 관리자 역할로 이관하고 임시 bootstrap 경로를 비활성화한다.
- 이 전환을 테스트 항목으로 명시해 임시 권한이 운영에 남지 않게 했다.

### 데이터·이벤트 소유권

- 한 테이블은 한 모듈만 소유한다.
- 다른 모듈 변경은 application interface 또는 outbox event를 사용한다.
- Alembic head, OpenAPI 생성물, lockfile, 공통 UI 토큰은 Integration Agent가 최종 소유한다.

### AI 범위

- Phase 5 이전에는 검색/RAG를 활성화하지 않는다.
- Phase 6 이전에는 AI 쓰기 도구를 활성화하지 않는다.
- AI의 DB 직접 접근과 승인 우회는 전체 단계에서 금지한다.

## 3. 범위 검토

전체 71개 작업은 설계·의존성·종료 게이트 수준으로 계획했다. 파일·테이블·API·이벤트·테스트까지 원자화한 상세 실행계획은 **Phase 0**에 집중했다.

이 구분은 의도적이다. Phase 1 이후의 정확한 파일 경로와 공통 helper는 Phase 0에서 실제 확정되는 저장소 패턴, 권한 엔진, audit/outbox, generated client에 의존한다. 이후 단계는 각 직전 단계 게이트에서 같은 양식으로 상세 계획을 확정해야 불필요한 재작성을 줄일 수 있다.

## 4. 명시적 기준안

아래 선택은 구현계획의 기본값이며 설계 범위를 바꾸지 않는다.

- GitLab CI를 기준 예시로 사용하되 CI 명령은 공급자에 독립적으로 작성한다.
- backend는 한 Python 코드베이스에서 API·worker·scheduler entrypoint를 분리한다.
- browser 인증은 HttpOnly 보안 세션 쿠키와 서버측 철회를 사용한다.
- MFA 1차 방식은 TOTP다.
- 개발·스테이징·운영은 Docker Compose manifest를 분리한다.
- PostgreSQL, Redis, MinIO는 Phase 0부터 사용하고 OpenSearch·Qdrant는 Phase 5에 활성화한다.
- 초기 관리자 bootstrap 경로는 RBAC 전환 후 폐기한다.

## 5. 구현 전 확인할 운영 설정

다음 값은 설계 승인 사항이 아니라 실제 배포 시 입력할 기준정보다.

- 실제 사내 도메인과 내부 DNS
- 서버 OS·스토리지·백업 대상 경로
- Git 저장소 공급자
- 이메일·캘린더 서비스
- 회사·부서·직원 초기 데이터
- VPN 또는 사내망 접근 방식
- 백업 암호화 키 보관 위치
- 관리자 MFA 적용 범위
- 외부 회계 시스템
- 로컬 AI 추론 서버 위치와 모델 정책

운영값을 아직 정하지 않아도 `WP-PLT-001`은 시작할 수 있다. 네트워크·백업 관련 값은 `WP-OPS-001`과 `WP-OPS-002` 전에 실제 환경 변수로 채운다.

## 6. 검토 결론

- 설계와 구현계획 사이의 핵심 모순은 발견되지 않았다.
- 71개 작업의 dependency는 유효하다.
- Phase 0은 에이전트가 바로 작업 계약을 작성할 수 있는 수준으로 세분화됐다.
- 구현 시작 전 남은 절차는 이 구현계획에 대한 사용자 승인이다.
