# WP-PKD-MAIL-APPROVAL-20260909 — 메일 및 첨부 승인 분류

## 사용자 승인 범위와 설계

사용자 2026-09-09 요청: 하이웍스 메일 파일 연동, 사용자가 승인한 뒤 프로젝트 분류, 분류/미분류 구분. 이 요청이 이번 기능 변경의 승인이다. 기존 전체 프로젝트 권한 정책(ADR-020)은 별개이며 이번 좁은 메일 승인 흐름 때문에 작업을 중단하지 않는다.

- 도메인/키워드 분류는 추천일 뿐이다. 모든 새 메일은 unclassified + project_id=null로 시작한다. suggested_project_id는 별도 필드다. 기존 메모리 overlay는 승인 근거로 인정하지 않는다.
- 현재 IAM이 admin/member 두 역할뿐이므로 메일 공용 검토함·승인/제외/원본 미분류 첨부 조회는 active admin(mail.review)에 한정한다. 승인 메일/첨부 조회는 admin 또는 해당 프로젝트 생성자에 한정한다. 외부/비활성/AI 별도 권한 모델은 아직 없으므로 새 우회 헤더/acting-user를 허용하지 않는다. 이는 전체 프로젝트 공유 정책을 바꾸지 않는 좁은 메일 자원 정책이다.
- 승인 요청에는 project_id, expected_version(초기0), attachments[{part_index,category}], Idempotency-Key를 명시한다. 아무 파일도 미리 체크하지 않는다. 승인한 첨부만 documents의 공개 인터페이스를 통해 프로젝트 드라이브에 연결한다. 파일 선택 없음은 메일만 승인하는 유효한 선택이다.
- 미분류→project(분류 완료) 또는 unrelated(명시 제외)만 지원한다. 이미 분류된 메일의 다른 프로젝트 이동은 이번 범위에서 409로 거부한다. 동일 키/동일 payload 재시도는 기존 결과 반환, 다른 payload는409. 별도 키라도 이미 승인된 상태는409. CAS 및 원자 transaction으로 중복 파일과 부분 승인 방지.
- 업무 데이터는 mail-owned review/audit 테이블 및 documents-owned mail attachment reference 테이블에 영속화한다. 식별자는 mailbox_key(호스트/계정의 비가역 해시, 비밀번호 제외)+UIDL로 분리한다. binary는 DB 저장 금지.
- 이번 파일 연동은 원본 메일 첨부의 승인된 참조다. 서버에 파일 복사·scan-ready로 표시하지 않는다. 승인 시 선택 첨부 bytes를 가져와 실제 이름/MIME/크기/SHA256을 확정하고, 다운로드 시 같은 첨부인지 검증한다. 원본이 삭제되면 명확히 오류를 반환한다. 드라이브에 '메일 원본 연결'을 표시한다. 파일 영구보관/새 upload·scan 파이프라인은 별도 기능이다.
- 메일 화면 탭 all/unclassified/project/unrelated + page/선택메일은 URL에 반영한다. 기본 unclassified. admin은 공용 미분류 전체를 볼 수 있고, classified는 현재 프로젝트 승인건만. 상세 선택 ID가 목록 밖이면 서버의 actor 범위 검증 후 classification=project 및 project_id=현재 경로 프로젝트를 재검증한 경우만 표시한다(드라이브 출처 링크 지원). 실패하면 다른 메일을 대신 보여주지 않는다. 프로젝트 추천과 승인 상태를 명확히 구분하고, 승인 전 지식화도 서버에서 거부한다.

## 파일 소유권 및 공통 계약

### mail_backend (이전 wbs_claude 조정자)

소유: modules/mail/**, mail 관련 신규 tests, 기존 test_real_adapters의 분류 기대값만, common/schema.py 모델 등록, projects/api/routes.py의 unclassified_count 호출 부분, 새 scripts/migrate_mail_review.py, docs/work-packages/WP-PKD-MAIL-BACKEND.md.
다른 모듈 내부 import/DB쓰기 금지. documents.public만 통해 연결. 기존 converter/AI/WBS/메일첨부 변경은 보존한다.

계약:
- MailOut 기존 필드 유지 + suggested_project_id:str|null, version:int(초기0), approved_by:str|null, approved_at:datetime|null, attachments[].linked_file_id:str|null, can_review:bool(현재 actor).
- GET /api/v1/projects/{project_id}/mail?status=unclassified|project|unrelated|all&offset=0&limit=50. meta 기존 collection 형식(total/next_cursor/has_more) 준수. 페이지는 요청 offset/limit으로 계산한다. admin 미분류=공용검토함; project=현재 프로젝트 승인만. 비admin은 해당 프로젝트 생성자라면 승인건만 조회 가능, 미분류/제외는403.
- GET /api/v1/projects/{project_id}/mail/counts -> Envelope[{unclassified:int,project:int,unrelated:int,all:int}] (data는 객체). nonadmin 검토불가 count는0, project 허용건만.
- GET /api/v1/mail/{id}: 해당 actor 범위 확인. project_id/suggested_project_id는 분리.
- POST /api/v1/mail/{id}/approve body={project_id,expected_version,attachments:[{part_index,category}]} + Idempotency-Key -> Envelope[MailOut]. 허용 category original/report/deliverable/source.
- POST /api/v1/mail/{id}/attachments/approve body={expected_version,attachments:[{part_index,category}]} + Idempotency-Key -> Envelope[MailOut]. admin이 이미 승인한 메일의 미연결 첨부를 추가 승인한다. 기존 프로젝트는 고정하며 version 증가와 감사·원자성·재시도 규칙을 적용한다.
- POST /api/v1/mail/{id}/dismiss body={expected_version} + Idempotency-Key -> Envelope[MailOut]. idempotency 승인과 동일.
- GET /api/v1/mail/{id}/attachments/{part}: pending admin 미리보기 허용. approved 비admin은 승인·연결된 파일만. sha/size 불일치409, 원본 없음404, attachment/nosniff response, 다운로드 감사. 선택 query linked_file_id가 있으면 현재 mailbox의 승인첨부 ID와 일치해야 하며 불일치는404(계정교체 UIDL 재사용 방어).
- promote-to-note는 approved 상태/범위 먼저 검증하고 기존 사용 흐름 유지. 중복 지식화 상태 DB저장. 새로운 mail workflow endpoints는 모두 sync def.

### documents_links (이전 documents_claude)

소유: documents/infrastructure/mail_links.py 및 필요한 신규 models, documents/public.py/application/services.py/api/routes.py/domain/entities.py에서 메일 첨부 참조 연결 부분, tests/test_mail_drive_links.py, docs/work-packages/WP-PKD-MAIL-DRIVE.md. converter/ports는 기존 완료 변경 보존.
- documents.public.register_mail_attachments(db, *, project_id:str, mailbox_key:str, message_id:str, attachments:list[MailAttachmentLinkInput], actor_id:str) -> list[MailAttachmentLinkRef]
- documents.public에 재수출할 dataclasses:
  MailAttachmentLinkInput(part_index:int,name:str,content_type:str,size_bytes:int,sha256:str,category:str)
  MailAttachmentLinkRef(id:str,part_index:int)
- 함수는 호출자 transaction에 참여(내부 commit금지). 프로젝트 존재 확인, safe metadata, allowed category/hash/size 검증, UUID+unique(mailbox_key,message_id,part_index), 기존 다른프로젝트/metadata 불일치409. 읽기 목록은 documents table만조회, mail DB직접조회금지.
- DriveFile 기존 필드 유지 + source_mail_id:str|null=None, source_part_index:int|null=None, source_kind:str|null=None, sha256:str|null=None. origin='메일 원본 연결', source_kind='mail_attachment'. 기존 drive list/summary에 DB링크 합쳐 표시. DriveFileOut 동일 추가.
- Drive download는 기존 /api/mail/{id}/attachments/{part} 프록시를 사용한다(백엔드 mail workflow가 승인/권한/hash를 검증). Drive 다운로드에는 linked_file_id=file.id query를 전달한다. 출처메일 링크도 같은 query를 포함하고 상세 attachments에 해당 linked_file_id가 있는지 UI에서 검증한다. 새 일반 upload/scanner 구현하지 않는다.
- common/schema.py는 mail 담당만 수정. 새 document models의 정확한 import 경로를 즉시 mail 담당/총괄에게 전달.

### mail_frontend (이전 ai_claude)

소유: mail page, drive page/widget에서 링크 표시, 신규 src/widgets/mail/**(폼+테스트), 새 shared/data/mail-review.ts 및 mail-review-actions.ts, packages/api-client/src/domain.ts의 Mail/Drive타입만, 기존 attachment proxy의 오류/헤더 안전처리 필요부분, docs/work-packages/WP-PKD-MAIL-UI.md.
- 기존 shared actions.ts/gateway.ts의 메일 helper는 기존 경로 보존하되 신규 화면에서 사용하지 않아도 됨. 신규 helpers에서 auth cookies/ProblemDetails 패턴 재사용.
- 승인 폼: 명시적 프로젝트 선택(현재프로젝트/추천은 정보), 기본선택 없는 첨부 checkbox + 분류 선택 + 최종 명시적 승인 버튼. 승인 요청 전에 프로젝트/선택파일 요약 확인가능. 오류·충돌·중복 클릭 pending·권한 없음 상태. 같은 논리 재시도는 같은 Idempotency-Key 유지, 폼내용 변경/성공후는 새키.
- 탭·counts·pagination·상태배지. member는 승인폼 숨김·승인목록만. 첨부별 대기/연결완료 표시. 드라이브파일은 출처메일/다운로드링크 명시, 링크만 있고 로컬 저장된 것으로 표시금지.
- API counts data 객체, Mail response 위 계약 준수. 타입 필드 추가에서 기존 AI/메일첨부 변경 보존.

## 작업 필수 항목

Work Package ID: WP-PKD-MAIL-APPROVAL-20260909
Owned Module: mail 승인, documents 메일 참조, 관련 frontend
Goal: 사람 승인 없이는 프로젝트/첨부 연결 없음, 상태 명확 구분
In Scope: 추천/승인 분리, 영속상태, 선택파일링크, 권한/감사/CAS/idempotency, 필터 UI
Out of Scope: 이메일 발송/삭제/읽음변경, 실제 개인정보 테스트, 일반 DMS 업로드/스캔·영구복사, 다른 ERP 모듈
Dependencies: 기존 IAM/projects 공개 인터페이스, 신규 module-owned additive schema
API/Event contracts used: 위 새/확장 /api/v1 계약. 이벤트 발행 없음(단일 transaction public interface)
Tables owned: mail review/audit, documents attachment link. 각 소유 모듈만쓰기
Permissions affected: mail.review=active admin; approved read=active admin/project creator; 미승인 AI 실행불가
Migration needed: 신규 테이블만 추가. 기존 테이블/적용migration 수정 없음. 새 스크립트에서 명시적 --apply, DSN출력금지, 재실행가능
Tests required: 자동분류방지/승인파일선택/재시작/중복payload/버전충돌/타project/권한/비활성/없는첨부/원본해시변경/rollback/분류탭/빈상태/상호작용, 전체 회귀
Risks/assumptions: 메일 첨부는 승인된 원본참조이며 원본메일 삭제시 접근불가. 운영 점검/배포는 로컬 검증후 서버 상태와 충돌여부 확인

모든 제품/테스트 코드는 Claude Code --model sonnet --effort medium으로 작성. Codex 조정자는 검토·실행·문서만. 테스트는 fixture만. 로그/임시 테스트는 gitignored .mail-review-runs 또는 .task-runs 아래(Windows ACL 호환 경로). 기존 작업을 되돌리지 않는다.

## 운영 사전 점검 (2026-09-09)

- SSH 읽기 점검: `/opt/luminode/ERP` HEAD `8313e3e`, working tree clean. 로컬 HEAD `e6dcfbd`와 서버 HEAD의 tree diff가 비어 있어 현재 공통 원본 파일 내용이 같다.
- api/web/db 컨테이너 healthy, Ollama 실행 중. API readiness HTTP 200, web `/login` HTTP 200.
- 실제 메일 내용·첨부·직원/고객 DB 행은 열지 않았다. 이번 단계에서 운영 코드/스키마/설정은 변경하지 않았다.
- 배포 전 새 승인 흐름의 전체 회귀·타입·경계·빌드 검사를 수행한다. 운영 반영 시 별도 생성한 이전 이미지 태그와 원본 파일 복구본을 보존하고, 이번 mail/documents/UI 파일만 전달한다. 기존 AI/WBS/converter 작업은 독립 변경이다.
- 스키마는 신규 승인/감사/첨부참조 테이블만 추가한다. 기존 테이블 변경·데이터 재분류 backfill·원본메일 변경 없음. 되돌릴 때 신규 감사/승인 데이터는 삭제하지 않고 보존한다.

## 사용자 요청에 따른 종료·인계
2026-09-09 사용자 토큰 절감 및 일시중단 지시로 작업을 동결했다. 최종 상태는 ../HANDOFF-2026-09-09-MAIL-APPROVAL.md 참조. 로컬 backend299/frontend118 및 frontend build PASS, Ruff import정렬1건 남음. 서버 배포·운영migration·PostgreSQL실행검증은 수행하지 않았다. 새 사용자 요청 전 재개하지 않는다.
