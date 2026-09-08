# 우분투 서버 배포

사내 우분투 서버에 전체를 올린다. 서버에 미리 깔아야 할 것은 **도커 하나뿐**이고,
그마저 `deploy.sh`가 없으면 설치한다.

## 서버에 없는 다섯 가지를 어떻게 해결하는가

| 없는 것 | 해결 | 서버에 설치하나 |
|---|---|---|
| kordoc | 백엔드 이미지에 npm으로 넣는다 | 아니오, 이미지 안 |
| 옵시디언 | 볼트는 마크다운 폴더다. 앱이 필요 없다 | 아니오 |
| 깃허브 | REST API 호출. 토큰만 있으면 된다 | 아니오 |
| 하이웍스 | 표준 IMAP으로 읽는다. API 신청이 필요 없다 | 아니오 |
| 한컴 | hwpx는 XML을 담은 ZIP이다. kordoc이 직접 만든다 | **필요 없음** |

한컴 오피스가 없어도 되는 이유를 조금 더 적는다. hwpx는 개방된 파일 형식이고
kordoc의 의존성은 `jszip`, `@xmldom/xmldom`, `markdown-it`, `cfb`처럼 전부 순수
자바스크립트다. 네이티브 모듈도 OS 제한도 없고 요구사항은 Node 18 이상뿐이다.
한글 문서를 만들기 위해 한글 프로그램이 필요하지 않다.

옵시디언도 같은 성격이다. 볼트는 `.md` 파일이 든 폴더이고 `[[위키링크]]`는
텍스트다. 애플리케이션은 파일을 읽어 백링크 색인을 만들 뿐이라 GUI 앱이 서버에
있을 이유가 없다. 편집은 사내 PC의 옵시디언에서 계속한다.

## 설치

```bash
git clone https://github.com/SunhSOO/ERP.git
cd ERP/infra
cp .env.example .env
$EDITOR .env          # 아래 "연동 켜기" 참조
./deploy.sh
```

`deploy.sh`가 하는 일이다.

1. 도커가 없으면 설치한다. 도커 공식 저장소에 해당 우분투 코드명이 아직 없으면
   우분투 기본 패키지(`docker.io`, `docker-compose-v2`)로 넘어간다
2. 볼트 디렉터리를 만들고 컨테이너 사용자가 쓸 수 있게 소유자를 맞춘다
3. 이미지를 빌드하고 기동한다
4. `/health/live`와 `kordoc --version`으로 실제 동작을 확인한다

우분투 26.04를 기준으로 썼고 22.04와 24.04에서도 같은 절차가 동작한다.

## 연동 켜기

기본값은 전부 픽스처다. 필요한 설정이 갖춰진 것만 켠다. 설정이 빠진 채로 켜면
픽스처로 남으면서 그 사유를 화면 09에 표시한다. 조용히 대체하지 않는다.

### 깃허브

```bash
LEP_ADAPTER_VCS=github
LEP_GITHUB_TOKEN=ghp_...        # repo 읽기 권한이면 충분하다
LEP_GITHUB_REPO=SunhSOO/ERP
```

토큰은 `infra/.env`에만 둔다. 이 파일은 저장소에 올라가지 않는다.

### 옵시디언 볼트

사내 PC에서 볼트를 올린다.

```bash
./sync-vault.sh "/c/Users/sunhy/Desktop/행수지식" lep@서버 /opt/luminode/ERP/infra/vault
# 무엇이 바뀔지 확인한 뒤
./sync-vault.sh "/c/Users/sunhy/Desktop/행수지식" lep@서버 /opt/luminode/ERP/infra/vault --apply
```

그다음 `.env`에서 켠다.

```bash
LEP_ADAPTER_VAULT=obsidian
LEP_VAULT_HOST_PATH=./vault
```

서버가 만든 노트를 PC로 가져올 때는 `--pull`을 쓴다. 스크립트는 `--delete`를
쓰지 않는다. 한쪽에서 지운 파일이 반대쪽에서 사라지면 사용자의 노트를 잃는다.

### 하이웍스 메일

먼저 하이웍스에서 **메일 > 환경설정 > 기본 설정**의 POP3/IMAP을 사용함으로 켠다.
이 절차 없이는 어떤 메일 클라이언트도 붙지 못한다.

```bash
LEP_ADAPTER_MAIL=hiworks
LEP_HIWORKS_USER=pm@회사도메인
LEP_HIWORKS_PASSWORD=...
LEP_HIWORKS_PROJECT_DOMAINS={"고객사도메인.co.kr":"prj-daon"}
```

발신 도메인이 자동 분류의 기준이다. 읽기 전용으로 접속하므로 메일을 지우거나
읽음 표시를 남기지 않는다.

IMAP 주소는 `imaps.hiworks.com:993`을 기본값으로 뒀다. 가비아 문서가 확인해 주는
것은 `pop3s.hiworks.com:995`와 `smtps.hiworks.com:465`이므로, IMAP이 열리지 않으면
`LEP_HIWORKS_HOST`와 `LEP_HIWORKS_PORT`를 조정한다. 계정 관리자에게 확인이 필요한
부분이다.

### 문서 변환

이미지에 이미 들어 있어 기본으로 켜져 있다. 끄려면 `LEP_ADAPTER_CONVERTER=fixture`.

### 로컬 LLM

어댑터는 아직 없다(WP-PKD-033). 서버만 미리 띄우려면 프로파일을 쓴다.

```bash
docker compose --profile llm up -d
docker compose exec ollama ollama pull llama3.1:8b
```

GPU를 쓰려면 호스트에 NVIDIA Container Toolkit이 필요하다. 없으면
`docker-compose.yml`의 `deploy.resources` 블록을 지우고 CPU로 돌린다.

## 공개 범위

기본은 루프백이라 서버 밖에서 보이지 않는다. 사내망에 열려면 `.env`에서 바꾼다.

```bash
LEP_WEB_BIND=0.0.0.0
LEP_WEB_PORT=3000
```

백엔드 포트는 호스트로 내보내지 않는다. 웹만 컨테이너 네트워크 안에서 API에
닿는다. 인증이 아직 없으므로(WP-PKD-021) 인터넷에 직접 노출하지 않는다. 사내망
안쪽이나 역방향 프록시 뒤에 둔다.

## 운영

```bash
docker compose ps                 # 상태
docker compose logs -f api        # 로그. 구조화 JSON이고 trace_id가 들어 있다
docker compose restart api        # 재시작
docker compose down               # 중지
git pull && docker compose up -d --build   # 갱신
```

## 확인 항목

기동 후 화면 09(AI·로컬 LLM 설정)의 연동 자격증명 카드가 실제 상태를 보여준다.
켠 것은 연결됨, 켜지 않은 것은 무엇이 필요한지 함께 표시된다.

- `/home` 프로젝트 카드가 렌더된다
- 화면 05에서 변환 실패 문서의 "다시 시도"가 실제 hwpx를 만든다
- 화면 04가 볼트의 실제 노트 수를 보여준다
- 화면 07이 저장소 이름과 정합률을 보여준다

## 아직 없는 것

- **영속성.** 데이터는 프로세스 메모리에 있고 재시작하면 초기화된다. 볼트에 쓴
  노트와 생성된 hwpx만 파일로 남는다. PostgreSQL은 WP-PKD-020이다
- **인증.** 접속에 로그인이 없다. WP-PKD-021 전까지 사내망 안쪽에만 둔다
- **로컬 LLM 어댑터.** 과업지시서 분류와 회의록 추출은 아직 픽스처다.
  하이웍스 메일의 의도 판정도 모델이 아니라 키워드 규칙이라 신뢰도를 낮음으로
  보고한다
- **이미지 빌드 검증.** 개발 장비에 도커가 없어 이 Dockerfile들은 서버에서 처음
  빌드된다. 실패하면 `docker compose build api` 또는 `build web`으로 어느 쪽인지
  좁힌다
