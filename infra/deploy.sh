#!/usr/bin/env bash
# 우분투 서버 부트스트랩과 기동.
#
#   git clone https://github.com/SunhSOO/ERP.git && cd ERP/infra
#   cp .env.example .env && $EDITOR .env
#   ./deploy.sh
#
# 우분투 26.04를 기준으로 하되 22.04와 24.04에서도 동작한다. 도커가 없으면
# 설치하고, 이미 있으면 건드리지 않는다.
#
# 서버에 필요한 것은 도커뿐이다. Node, 파이썬, kordoc, 한컴 오피스, 옵시디언 앱은
# 설치하지 않는다. Node와 kordoc은 이미지 안에 들어가고, hwpx는 kordoc이 직접
# 만들기 때문에 한컴이 필요 없으며, 볼트는 마크다운 폴더라 앱이 필요 없다.

set -euo pipefail

INFRA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$INFRA_DIR"

log() { printf '\n\033[1m== %s ==\033[0m\n' "$*"; }
warn() { printf '\033[33m경고: %s\033[0m\n' "$*" >&2; }
die() { printf '\033[31m오류: %s\033[0m\n' "$*" >&2; exit 1; }

# ── 사전 확인 ────────────────────────────────────────────────────────────
[[ -f .env ]] || die ".env가 없다. cp .env.example .env 후 값을 채운다."

# 데이터베이스 비밀번호는 비어 있으면 만들어 채운다. 사람이 고른 짧은 값보다
# 낫고, .env에 남으므로 재기동해도 같은 값을 쓴다. 이미 값이 있으면 건드리지
# 않는다. 바꾸면 기존 pgdata 볼륨에 접속하지 못한다.
if ! grep -qE '^LEP_DB_PASSWORD=.+$' .env; then
    # 개행이 섞이지 않게 16진수 문자만 남긴다.
    generated="$(head -c 32 /dev/urandom | od -An -tx1 | tr -dc 'a-f0-9')"
    if grep -qE '^LEP_DB_PASSWORD=' .env; then
        # 값만 채운다. 구분자는 |다. 생성값이 16진수라 충돌하지 않는다.
        sed -i "s|^LEP_DB_PASSWORD=.*|LEP_DB_PASSWORD=${generated}|" .env
    else
        { echo; echo "LEP_DB_PASSWORD=${generated}"; } >> .env
    fi
    chmod 600 .env
    log "LEP_DB_PASSWORD를 새로 만들어 .env에 넣었다."
fi

if [[ -r /etc/os-release ]]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    log "호스트: ${PRETTY_NAME:-알 수 없음}"
    [[ "${ID:-}" == "ubuntu" ]] || warn "우분투가 아니다. 아래 설치 단계는 건너뛸 수 있다."
fi

# ── 도커 ─────────────────────────────────────────────────────────────────
install_docker() {
    log "도커 설치"
    sudo apt-get update
    sudo apt-get install -y ca-certificates curl gnupg

    # 도커 공식 저장소를 먼저 시도한다. 새 우분투는 도커가 아직 저장소를
    # 내지 않은 경우가 있어 그때는 우분투 기본 패키지로 넘어간다.
    local codename
    codename="$(. /etc/os-release && echo "${UBUNTU_CODENAME:-${VERSION_CODENAME:-}}")"
    local repo="https://download.docker.com/linux/ubuntu"

    if curl -fsSL --head "${repo}/dists/${codename}/Release" >/dev/null 2>&1; then
        sudo install -m 0755 -d /etc/apt/keyrings
        curl -fsSL "${repo}/gpg" | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        sudo chmod a+r /etc/apt/keyrings/docker.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] ${repo} ${codename} stable" \
            | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
        sudo apt-get update
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io \
            docker-buildx-plugin docker-compose-plugin
    else
        warn "도커 공식 저장소에 ${codename}이 아직 없다. 우분투 기본 패키지를 쓴다."
        sudo apt-get install -y docker.io docker-compose-v2
    fi

    sudo systemctl enable --now docker
}

if ! command -v docker >/dev/null 2>&1; then
    install_docker
else
    log "도커가 이미 있다: $(docker --version)"
fi

docker compose version >/dev/null 2>&1 \
    || die "docker compose 플러그인이 없다. docker-compose-plugin 또는 docker-compose-v2를 설치한다."

# sudo 없이 docker를 쓰려면 그룹에 들어가야 한다. 지금 세션에는 적용되지 않는다.
if ! docker info >/dev/null 2>&1; then
    if getent group docker >/dev/null && ! id -nG "$USER" | grep -qw docker; then
        log "$USER를 docker 그룹에 추가"
        sudo usermod -aG docker "$USER"
        warn "다시 로그인해야 적용된다. 지금은 sudo로 이어서 진행한다."
    fi
    DOCKER="sudo docker"
else
    DOCKER="docker"
fi

# ── 볼트 디렉터리 ────────────────────────────────────────────────────────
VAULT_PATH="$(grep -E '^LEP_VAULT_HOST_PATH=' .env | cut -d= -f2- || true)"
VAULT_PATH="${VAULT_PATH:-./vault}"
if [[ ! -d "$VAULT_PATH" ]]; then
    log "볼트 디렉터리 생성: $VAULT_PATH"
    mkdir -p "$VAULT_PATH"
fi
# 컨테이너의 lep 사용자(uid 10001)가 노트를 쓸 수 있어야 한다.
sudo chown -R 10001:10001 "$VAULT_PATH" 2>/dev/null \
    || warn "볼트 소유자를 바꾸지 못했다. 지식화가 실패하면 uid 10001에 쓰기 권한을 준다."

# ── 기동 ─────────────────────────────────────────────────────────────────
log "이미지 빌드와 기동"
$DOCKER compose up -d --build

log "상태"
$DOCKER compose ps

# ── 확인 ─────────────────────────────────────────────────────────────────
log "기동 확인"
for _ in $(seq 1 60); do
    if $DOCKER compose exec -T api python -c \
        "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/health/live',timeout=2)" \
        >/dev/null 2>&1; then
        echo "api 정상"
        break
    fi
    sleep 2
done

echo
# 셰방에 기대지 않고 node로 직접 부른다. 백엔드도 같은 방식으로 실행한다.
KORDOC_CLI=/usr/local/lib/node_modules/kordoc/dist/cli.js
echo "kordoc: $($DOCKER compose exec -T api node "$KORDOC_CLI" --version 2>/dev/null | tail -1 || echo '확인 실패')"

WEB_PORT="$(grep -E '^LEP_WEB_PORT=' .env | cut -d= -f2- || true)"
echo
echo "웹: http://localhost:${WEB_PORT:-3000}/"
echo
echo "첫 접속은 가입 화면으로 간다. 이 서버의 첫 계정이 관리자가 된다."
echo "프로젝트는 비어 있다. 만들면 볼트에 프로젝트 코드 폴더가 하나 생긴다."
