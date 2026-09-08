# 백엔드 이미지.
#
# 파이썬 애플리케이션이지만 Node도 함께 들어간다. kordoc이 Node CLI이고 백엔드가
# 그것을 하위 프로세스로 부르기 때문이다. 한컴 오피스는 필요 없다. hwpx는 XML을
# 담은 ZIP이고 kordoc이 순수 자바스크립트로 직접 만든다.
#
# 빌드 컨텍스트는 저장소 루트다.
#   docker build -f infra/api.Dockerfile -t lep-api .

# ── Node 런타임과 kordoc ──────────────────────────────────────────────────
FROM node:22-bookworm-slim AS kordoc

# 버전을 고정한다. 변환 결과가 배포마다 달라지면 안 된다.
ARG KORDOC_VERSION=4.13.1
RUN npm install -g "kordoc@${KORDOC_VERSION}" \
    && node -e "require('child_process').execSync('kordoc --version',{stdio:'inherit'})"

# ── 파이썬 런타임 ────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    # 한국어 문서를 다루므로 UTF-8을 강제한다. 기본 로케일이 무엇이든
    # 하위 프로세스 출력이 깨지지 않는다.
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PATH="/app/.venv/bin:${PATH}"

# tini는 uvicorn이 컨테이너 종료 신호를 제대로 받게 한다.
# ca-certificates는 깃허브·하이웍스 TLS 연결에 필요하다.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates tini \
    && rm -rf /var/lib/apt/lists/*

# 위 단계에서 만든 Node와 전역 설치된 kordoc을 그대로 가져온다.
# 두 이미지 모두 bookworm이라 glibc가 호환된다.
COPY --from=kordoc /usr/local/bin/node /usr/local/bin/node
COPY --from=kordoc /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s /usr/local/lib/node_modules/kordoc/dist/cli.js /usr/local/bin/kordoc \
    && chmod +x /usr/local/lib/node_modules/kordoc/dist/cli.js

# uv.lock이 revision 3이라 그 형식을 읽을 수 있는 버전이어야 한다.
# 잠금 파일을 만든 버전과 맞춰 둔다.
COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /usr/local/bin/uv

WORKDIR /app

# 의존성을 먼저 넣어 소스가 바뀌어도 이 계층이 재사용되게 한다.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY apps/backend/pyproject.toml ./apps/backend/pyproject.toml
COPY apps/backend/src ./apps/backend/src
COPY scripts ./scripts

# 루트로 돌리지 않는다. 볼트와 산출물 디렉터리는 이 사용자 소유여야 한다.
# 이름 있는 볼륨은 이미지 안의 같은 경로에서 소유권을 물려받는다. 여기서 미리
# 만들어 두지 않으면 도커가 root 소유로 만들고 uid 10001이 쓰지 못한다.
RUN useradd --create-home --uid 10001 lep \
    && mkdir -p /data/kordoc-out /data/vault /data/uploads \
    && chown -R lep:lep /app /data
USER lep

ENV PYTHONPATH=/app/apps/backend/src \
    LEP_KORDOC_OUTPUT_DIR=/data/kordoc-out

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=3).status==200 else 1)"

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "lep.bootstrap.app:app", "--host", "0.0.0.0", "--port", "8000"]
