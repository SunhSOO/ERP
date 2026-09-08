#!/usr/bin/env bash
# 옵시디언 볼트를 서버로 올린다.
#
#   ./sync-vault.sh "/c/Users/sunhy/Desktop/행수지식" lep@서버주소 /opt/luminode/ERP/infra/vault
#
# 서버에 옵시디언 앱을 설치할 필요가 없다. 볼트는 마크다운 파일 폴더이고,
# 애플리케이션은 그 파일을 읽을 뿐이다. 편집은 사내 PC의 옵시디언에서 한다.
#
# 서버가 만든 노트(메일·회의록 지식화 결과)를 PC로 가져오려면 --pull을 쓴다.

set -euo pipefail

usage() {
    cat <<'USAGE'
사용법:
  sync-vault.sh <로컬볼트> <사용자@서버> <서버경로> [--pull] [--apply]

  --pull   서버에서 로컬로 가져온다 (기본은 로컬 → 서버)
  --apply  실제로 전송한다 (기본은 무엇이 바뀔지만 보여주는 예행 연습)

.obsidian 설정 폴더와 .trash는 제외한다. 서버에는 필요 없고 기기마다 다르다.
USAGE
}

[[ $# -ge 3 ]] || { usage; exit 1; }

LOCAL_VAULT="${1%/}"
REMOTE_HOST="$2"
REMOTE_PATH="${3%/}"
shift 3

DIRECTION="push"
DRY_RUN="--dry-run"
for arg in "$@"; do
    case "$arg" in
        --pull) DIRECTION="pull" ;;
        --apply) DRY_RUN="" ;;
        *) usage; exit 1 ;;
    esac
done

command -v rsync >/dev/null 2>&1 || {
    echo "rsync가 필요하다. 윈도우라면 Git Bash 대신 WSL에서 실행하거나 scp를 쓴다." >&2
    exit 1
}

[[ -d "$LOCAL_VAULT" ]] || { echo "볼트를 찾을 수 없다: $LOCAL_VAULT" >&2; exit 1; }

EXCLUDES=(
    --exclude '.obsidian/'
    --exclude '.trash/'
    --exclude '.git/'
    --exclude '.DS_Store'
)

# --delete를 쓰지 않는다. 한쪽에서 지운 파일이 다른 쪽에서 사라지면
# 사용자의 노트를 잃는다. 정리는 사람이 직접 한다.
if [[ "$DIRECTION" == "push" ]]; then
    echo "로컬 → 서버: $LOCAL_VAULT  →  $REMOTE_HOST:$REMOTE_PATH"
    rsync -avz $DRY_RUN "${EXCLUDES[@]}" "$LOCAL_VAULT/" "$REMOTE_HOST:$REMOTE_PATH/"
else
    echo "서버 → 로컬: $REMOTE_HOST:$REMOTE_PATH  →  $LOCAL_VAULT"
    rsync -avz $DRY_RUN "${EXCLUDES[@]}" "$REMOTE_HOST:$REMOTE_PATH/" "$LOCAL_VAULT/"
fi

if [[ -n "$DRY_RUN" ]]; then
    echo
    echo "예행 연습이었다. 실제로 전송하려면 --apply를 붙인다."
fi
