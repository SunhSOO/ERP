# WP-PKD-MAIL-DRIVE — 승인 메일 첨부의 드라이브 참조

Work Package ID: WP-PKD-MAIL-DRIVE
Owned Module: documents
Goal: 승인한 메일 첨부의 불변 메타데이터를 프로젝트 드라이브에 연결
In Scope: 공개 등록 계약, 문서 소유 영속 참조, 중복/충돌/transaction 검증, 승인 참조 목록과 분류별 수량
Out of Scope: 첨부 영구복사, 일반 업로드, 악성코드 검사, 원본 메일 변경, converter 변경
Dependencies: ADR-021, mail 승인 application transaction, projects/iam public 인터페이스
API/Event contracts used: documents.public.register_mail_attachments, 기존 drive GET 응답 확장; 이벤트 없음
Tables owned: documents 메일 첨부 참조 테이블(신규)
Permissions affected: 승인 링크 조회는 active admin 또는 프로젝트 생성자. 등록은 승인 검증을 수행한 mail application에서 호출
Migration needed: 신규 모델 등록/추가 테이블만. 공통 schema/migration 스크립트는 mail 담당 소유
Tests required: 영속성, 동일 재시도, source 충돌, 안전 메타데이터, 원자 rollback, 권한, provenance
Risks/assumptions: 원본 메일 삭제/변경 시 다운로드 불가. 본 기능은 서버 파일 저장이나 scan-ready가 아님

## 계약

정확한 공유 계약은 [메일 승인 작업 패키지](2026-09-09-mail-approval.md)의 documents_links 절을 따른다. 등록 함수는 호출자 DB transaction에 참여하며 commit하지 않는다. 원본 식별자(mailbox_key, message_id, part_index)의 동일 재시도는 같은 참조를 반환하고, 다른 프로젝트나 다른 메타데이터는 409다.

바이너리는 저장하지 않는다. 이름·MIME·크기·SHA-256은 승인 흐름이 원본 bytes로 확정해 전달한다. 드라이브는 `메일 원본 연결`과 출처를 표시하고 기존 메일 첨부 다운로드 프록시를 사용한다. 해당 다운로드의 권한·원본 동일성·감사는 mail 소유 application이 검사한다.

## 검증 상태

문서 모듈의 구현 및 fixture 검증 완료. 전체 메일 승인·UI 통합 검증과 운영 적용은 총괄 작업에 포함한다.

## 검증 결과 및 완료 범위 (2026-09-09)

Completed Work Package: WP-PKD-MAIL-DRIVE
Files/Modules changed: documents/public.py, application/services.py, api/routes.py, domain/entities.py, 신규 infrastructure/mail_link_models.py 및 mail_links.py, tests/test_mail_drive_links.py
Behavior delivered: 승인된 원본 메일 첨부 참조를 UUID로 영속 등록. 동일 원본/동일 메타데이터는 기존 참조 반환, 다른 프로젝트·메타데이터는409. 빈 선택은 no-op이며 후속 첨부 추가 시 기존 링크 보존. 조회/분류 수량은 active admin 또는 프로젝트 생성자에게만 참조를 포함
API/Event contracts: register_mail_attachments 및 입력/반환 dataclasses 공개. 기존 drive files에 source_mail_id/source_part_index/source_kind/sha256 확장, offset/limit 페이지 처리. 이벤트 없음
Migrations: document_mail_attachment_links 신규 테이블. project/actor FK RESTRICT, FK 인덱스, 원본복합 unique 및 check. 공통 모델등록/추가 migration 스크립트는 mail 담당 소유
Permissions/Audit: 참조 등록은 mail 승인 transaction에서 호출하며 해당 승인/다운로드 감사는 mail 소유. documents는 created_by/created_at 보존. actor scope는 projects/iam 공개 인터페이스만 사용
Tests run and results: test_mail_drive_links.py 37 passed (9.98s), documents Ruff 통과, 소유7파일 strict mypy 통과. 테스트는 합성 fixture와 임시SQLite만 사용
Known limitations: 원본메일 영구보관/복사/검사/다운로드 자체는 documents 기능이 아님. source_mail_id는 opaque UIDL이고 다운로드는 기존 mail proxy + linked_file_id 검증을 사용. 메일 원본 삭제/변경/메일함 교체 시 mail API에서 오류가 반환된다. PostgreSQL/운영 서버 실동작 검증은 이번 fixture검증에 포함하지 않음
Follow-up dependencies: mail 승인·후속첨부 승인·감사·다운로드 검증, frontend 출처 표시/안전query, 총괄의 migration 및 통합 검증

### 회귀 근거

최초 SQLite outer rollback 실패를 재현한 뒤 첫 SAVEPOINT 이전 실제 outer transaction을 확립하여 해결했다. Savepoint 실패는 신규 batch만 취소하며 이미 승인된 링크와 호출자 transaction을 보존한다. CRLF filename/MIME, 정확 SHA256, 정수/분류/크기, source identity 충돌을 검사한다. 모델은 바이너리·scan-ready 값을 저장하지 않는다.

이번 메일 링크 변경은 기존 DocumentConverterPort/DocumentRepository만 사용한다. 이전 별도 작업의 ConversionArtifact/convert_with_artifact/kordoc 변경을 포함하지 않아도 메일 승인 참조 기능이 동작한다. 통합 경계 검사에서 문서 모듈 위반은 없었으며 동시에 작성 중이던 mail 내부 import1건은 담당자에게 전달했다.

