#!/bin/bash

# Docker Build and Push Script
# Rebuilds and pushes Flask and Streamlit applications to secured Docker registry

set -e

REGISTRY_URL="158.255.6.121:5000"
FLASK_IMAGE_NAME="flask-app"
STREAMLIT_IMAGE_NAME="streamlit-app"
TAG="${1:-latest}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;36m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    if [ ! -f "Dockerfile_flask_app" ]; then
        log_error "Dockerfile_flask_app not found in current directory"
        exit 1
    fi

    if [ ! -f "streamlit/Dockerfile_streamlit_app" ]; then
        log_error "streamlit/Dockerfile_streamlit_app not found"
        exit 1
    fi

    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

docker_login() {
    log_info "Authenticating with Docker registry: $REGISTRY_URL"

    if docker system info | grep -q "Registry: $REGISTRY_URL"; then
        log_info "Already authenticated with registry"
        return 0
    fi
echo "$DOCKER_USERNAME and $DOCKER_PASSWORD"
    if [ -z "$DOCKER_USERNAME" ] || [ -z "$DOCKER_PASSWORD" ]; then
        log_info "Please provide Docker registry credentials:"
        read -p "Username: " DOCKER_USERNAME
        read -s -p "Password: " DOCKER_PASSWORD
        echo
    fi

    echo "$DOCKER_PASSWORD" | docker login "$REGISTRY_URL" -u "$DOCKER_USERNAME" --password-stdin

    if [ $? -eq 0 ]; then
        log_success "Successfully authenticated with registry"
    else
        log_error "Failed to authenticate with registry"
        exit 1
    fi
}

build_image() {
    local dockerfile=$1
    local image_name=$2
    local context_dir=$3
    local full_image_name="$REGISTRY_URL/$image_name:$TAG"

    log_info "Building image: $full_image_name"
    log_info "Using dockerfile: $dockerfile"
    log_info "Build context: $context_dir"

    docker build -f "$dockerfile" -t "$full_image_name" "$context_dir"

    if [ $? -eq 0 ]; then
        log_success "Successfully built $full_image_name"
        return 0
    else
        log_error "Failed to build $full_image_name"
        return 1
    fi
}

push_image() {
    local image_name=$1
    local full_image_name="$REGISTRY_URL/$image_name:$TAG"

    log_info "Pushing image: $full_image_name"

    docker push "$full_image_name"

    if [ $? -eq 0 ]; then
        log_success "Successfully pushed $full_image_name"
        return 0
    else
        log_error "Failed to push $full_image_name"
        return 1
    fi
}

cleanup_local_images() {
    local image_name=$1
    local full_image_name="$REGISTRY_URL/$image_name:$TAG"

    read -p "Do you want to remove local image $full_image_name? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker rmi "$full_image_name"
        log_info "Removed local image: $full_image_name"
    fi
}

show_image_info() {
    local image_name=$1
    local full_image_name="$REGISTRY_URL/$image_name:$TAG"

    log_info "Image information for $full_image_name:"
    docker images "$full_image_name" --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.CreatedAt}}\t{{.Size}}"
}

main() {
    log_info "Starting Docker build and push process..."
    log_info "Registry: $REGISTRY_URL"
    log_info "Tag: $TAG"
    echo

    check_prerequisites
    echo

    docker_login
    echo

    log_info "=== Building Flask Application ==="
    if build_image "Dockerfile_flask_app" "$FLASK_IMAGE_NAME" "."; then
        show_image_info "$FLASK_IMAGE_NAME"
        echo

        log_info "=== Pushing Flask Application ==="
        push_image "$FLASK_IMAGE_NAME"
        echo
    else
        log_error "Skipping Flask app push due to build failure"
        exit 1
    fi

    log_info "=== Building Streamlit Application ==="
    if build_image "streamlit/Dockerfile_streamlit_app" "$STREAMLIT_IMAGE_NAME" "streamlit"; then
        show_image_info "$STREAMLIT_IMAGE_NAME"
        echo

        log_info "=== Pushing Streamlit Application ==="
        push_image "$STREAMLIT_IMAGE_NAME"
        echo
    else
        log_error "Skipping Streamlit app push due to build failure"
        exit 1
    fi

    log_success "=== Build and Push Summary ==="
    log_success "✓ Flask app: $REGISTRY_URL/$FLASK_IMAGE_NAME:$TAG"
    log_success "✓ Streamlit app: $REGISTRY_URL/$STREAMLIT_IMAGE_NAME:$TAG"
    echo

    log_info "=== Cleanup Options ==="
    cleanup_local_images "$FLASK_IMAGE_NAME"
    cleanup_local_images "$STREAMLIT_IMAGE_NAME"

    log_success "Docker build and push process completed successfully!"
}

show_help() {
    echo "Usage: $0 [TAG]"
    echo
    echo "This script builds and pushes Flask and Streamlit Docker images to a secured registry."
    echo
    echo "Arguments:"
    echo "  TAG          Image tag (default: latest)"
    echo
    echo "Environment Variables:"
    echo "  DOCKER_USERNAME    Docker registry username (optional, will prompt if not set)"
    echo "  DOCKER_PASSWORD    Docker registry password (optional, will prompt if not set)"
    echo
    echo "Examples:"
    echo "  $0                    # Build and push with 'latest' tag"
    echo "  $0 v1.0.0            # Build and push with 'v1.0.0' tag"
    echo "  DOCKER_USERNAME=user DOCKER_PASSWORD=pass $0 dev"
    echo
    echo "Expected file structure:"
    echo "  ./Dockerfile_flask_app"
    echo "  ./streamlit/Dockerfile_streamlit_app"
}

if [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
    show_help
    exit 0
fi

main
