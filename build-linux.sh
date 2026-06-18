#!/usr/bin/env bash
# Build Linux standalone executable using Docker
set -euo pipefail

IMAGE="zfs-tui-builder"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Building Docker image: $IMAGE"
docker build -t "$IMAGE" -f "$SCRIPT_DIR/Dockerfile.build" "$SCRIPT_DIR"

echo ""
echo "==> Building zfs-tui Linux executable..."
mkdir -p "$SCRIPT_DIR/dist"

docker run --rm \
    -v "$SCRIPT_DIR:/project" \
    -v "$SCRIPT_DIR/dist:/output" \
    "$IMAGE"

echo ""
echo "==> Done! Executable at: $SCRIPT_DIR/dist/zfs-tui"
ls -lh "$SCRIPT_DIR/dist/zfs-tui"
