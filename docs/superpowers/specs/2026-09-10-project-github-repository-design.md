# 프로젝트별 GitHub 저장소 연결 설계

## 목표

프로젝트 관리자가 각 프로젝트에 하나의 GitHub `owner/repository`를 연결·수정하고, 기존 WBS 정합 조회가 해당 연결을 사용한다.

## 경계와 보안

- integrations 모듈이 연결 설정과 감사 이력을 소유한다. GitHub 토큰은 기존 환경 변수만 사용하며 DB·API 응답·로그에 저장하지 않는다.
- `project_repository_connections`는 project UUID FK, provider=`github`, repository, version, audit columns를 가진다. 프로젝트별 하나의 GitHub 연결만 허용한다.
- `project_repository_connection_audit`는 변경 actor, 이전/새 repository, UTC 시각을 기록한다.
- active admin 또는 해당 프로젝트 생성자만 조회·수정할 수 있으며 서버가 항상 검사한다. 다른 프로젝트 설정은 변경할 수 없다.

## API와 동작

- `GET /api/v1/projects/{project_id}/vcs/connection`: 연결 또는 미연결 상태.
- `PUT /api/v1/projects/{project_id}/vcs/connection`: `{repository, expected_version}`. repository는 `owner/repository`만 허용하고 GitHub REST로 접근 가능 여부를 확인한 뒤 저장한다. 이전 값과 version이 다르면 409이다.
- 설정값이 있으면 VCS adapter가 환경 변수 매핑보다 우선한다. 없으면 기존 환경 변수 fallback을 유지한다.
- 저장 뒤 해당 프로젝트 VCS cache를 무효화한다. 저장소 내용을 변경하거나 GitHub token을 변경하지 않는다.

## UI

GitHub 연동 화면에 현재 연결, repository 입력, 연결 확인·저장, version 충돌 및 접근 오류를 표시한다. 수정 UI는 서버가 허용한 관리자/프로젝트 생성자에게만 보인다.

## 검증

연결 생성·수정·fallback·invalid format·GitHub 404/403·다른 프로젝트·비활성 사용자·version 충돌·감사 기록과 화면의 성공/오류 상태를 테스트한다. migration은 forward-safe create-only다.
