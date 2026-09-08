# 프론트엔드 이미지.
#
# pnpm 워크스페이스라 빌드 컨텍스트가 저장소 루트여야 한다. apps/web만으로는
# packages/ui와 packages/api-client를 찾지 못한다.
#
#   docker build -f infra/web.Dockerfile -t lep-web .

FROM node:22-bookworm-slim AS deps

ENV PNPM_HOME=/pnpm \
    PATH="/pnpm:${PATH}" \
    CI=1
RUN corepack enable

WORKDIR /repo

# 매니페스트와 잠금 파일만 먼저 복사해 설치 계층을 재사용한다.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/package.json
COPY packages/ui/package.json ./packages/ui/package.json
COPY packages/api-client/package.json ./packages/api-client/package.json
COPY packages/tsconfig/package.json ./packages/tsconfig/package.json
COPY packages/eslint-config/package.json ./packages/eslint-config/package.json

RUN pnpm install --frozen-lockfile

# ── 빌드 ─────────────────────────────────────────────────────────────────
FROM deps AS build

COPY packages ./packages
COPY apps/web ./apps/web

ENV NEXT_TELEMETRY_DISABLED=1

# 독립 실행형 출력은 여기서만 켠다. next.config.ts가 이 변수를 보고 결정한다.
# 개발 장비의 윈도우에서는 pnpm 워크스페이스의 심링크 권한 때문에 실패하므로
# 항상 켜 둘 수 없다. 이 줄이 없으면 아래 런타임 단계의 .next/standalone 복사가
# "failed to compute cache key: not found"로 죽는다.
ENV LEP_BUILD_STANDALONE=1

# 빌드 직후 산출물을 확인한다. 없으면 여기서 죽어야 한다. 다음 단계의
# COPY 실패 메시지보다 여기 메시지가 원인을 훨씬 잘 말해 준다.
# WORKDIR은 /repo이고 standalone은 워크스페이스 루트 기준으로 펼쳐진다.
RUN pnpm --filter @lep/web build \
    && test -f apps/web/.next/standalone/apps/web/server.js \
    || (echo "standalone 출력이 없다. LEP_BUILD_STANDALONE을 확인하라." >&2; exit 1)

# ── 런타임 ───────────────────────────────────────────────────────────────
FROM node:22-bookworm-slim AS runtime

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates tini \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10002 lep

WORKDIR /app

# standalone 출력은 실제로 쓰이는 파일만 담는다. node_modules 전체가 필요 없다.
COPY --from=build --chown=lep:lep /repo/apps/web/.next/standalone ./
COPY --from=build --chown=lep:lep /repo/apps/web/.next/static ./apps/web/.next/static

USER lep
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD node -e "require('http').get('http://127.0.0.1:3000/',r=>process.exit(r.statusCode<500?0:1)).on('error',()=>process.exit(1))"

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["node", "apps/web/server.js"]
