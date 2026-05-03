#!/usr/bin/env bash
# sim_macos.sh — build (first time) and run the macOS Docker sim
# environment. Browser-accessible GUI via noVNC.
#
# Usage:
#   bin/sim_macos.sh           # interactive shell inside the container
#   bin/sim_macos.sh build     # build/rebuild image only
#   bin/sim_macos.sh shell     # extra shell into a running container
#   bin/sim_macos.sh stop      # stop and remove the container
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="ros2-gem:macos"
CONTAINER="ros2-gem-macos"
WORKSPACE_HOST="$REPO/Sim/Cartagena_GEM_E4_workspace/ros2_ws"
CONTAINERFILE="$REPO/Sim/macos/Containerfile.macos"
ENTRYPOINT="$REPO/Sim/macos/entrypoint.sh"

cmd="${1:-run}"

# ─── Helpers ───
ensure_docker_running() {
    if ! docker info >/dev/null 2>&1; then
        echo "Docker daemon is not running."
        echo "Attempting to launch Docker Desktop..."
        open -a Docker 2>/dev/null || {
            echo "Could not auto-launch Docker Desktop. Open it manually and re-run."
            exit 1
        }
        echo "Waiting up to 60s for Docker to start..."
        for i in $(seq 1 60); do
            if docker info >/dev/null 2>&1; then
                echo "Docker is up."
                return 0
            fi
            sleep 1
        done
        echo "Docker did not start in 60s. Open Docker Desktop manually and retry."
        exit 1
    fi
}

build_image() {
    ensure_docker_running
    cp "$ENTRYPOINT" "$REPO/Sim/macos/entrypoint.sh.tmp" 2>/dev/null || true
    echo "Building $IMAGE (first time: ~5 GB, 20-30 min, only happens once)..."
    docker build \
        -t "$IMAGE" \
        -f "$CONTAINERFILE" \
        "$REPO/Sim/macos"
    echo "Build complete."
}

run_container() {
    ensure_docker_running

    if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
        build_image
    fi

    # Stop existing container if running
    if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
        docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
    fi

    echo
    echo "Starting container..."
    echo "GUI: http://localhost:6080/vnc.html  (open in your browser after Docker says 'Connected')"
    echo "Workspace mounted at /root/ros2_ws (lives at $WORKSPACE_HOST on host)"
    echo

    docker run -it --rm \
        --name "$CONTAINER" \
        -p 6080:6080 \
        -p 5900:5900 \
        -v "$WORKSPACE_HOST:/root/ros2_ws" \
        "$IMAGE"
}

case "$cmd" in
    run|"")
        run_container
        ;;
    build)
        build_image
        ;;
    shell)
        ensure_docker_running
        docker exec -it "$CONTAINER" bash -c \
            "source /opt/ros/humble/setup.bash; \
             [ -f /root/ros2_ws/install/setup.bash ] && source /root/ros2_ws/install/setup.bash; \
             exec bash"
        ;;
    stop)
        docker rm -f "$CONTAINER" 2>/dev/null || true
        echo "Stopped."
        ;;
    *)
        echo "Usage: $0 [run|build|shell|stop]"
        exit 1
        ;;
esac
