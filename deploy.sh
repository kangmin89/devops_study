#!/bin/bash
set -e

echo "=========================================="
echo "🚀 MLOps Blue-Green Zero downtime Deploy"
echo "=========================================="

IMAGE_NAME=${1:-mlops-sentiment-api:latest}
export DOCKER_IMAGE=$IMAGE_NAME

echo "📥 Pulling the latest image: $DOCKER_IMAGE"
docker pull $DOCKER_IMAGE

# 현재 활성화된(Nginx가 바라보고 있는) 환경을 가져오기
ACTIVE_ENV=$(docker compose exec nginx cat /etc/nginx/conf.d/default.conf | grep -q "http://blue:8000;" && echo "blue" || echo "green")

if [ "$ACTIVE_ENV" = "blue" ]; then
    TARGET_ENV="green"
else
    TARGET_ENV="blue"
fi

echo "🔄 Current Active: [$ACTIVE_ENV]. Deploying new version to [$TARGET_ENV]..."

# 타겟 컨테이너 띄우기 (최신 이미지)
docker compose up -d $TARGET_ENV

# 헬스체크 대기 로직
echo "⏳ Waiting for [$TARGET_ENV] container to become healthy..."
retries=0
MAX_RETRIES=15
while [ $retries -lt $MAX_RETRIES ]; do
    status=$(docker inspect --format='{{json .State.Health.Status}}' $(docker compose ps -q $TARGET_ENV) 2>/dev/null || echo "starting")
    
    if [ "$status" = '"healthy"' ] || [ "$status" = "healthy" ]; then
        echo "✅ [$TARGET_ENV] is fully healthy and ready to serve traffic!"
        break
    fi
    echo "   ... checking status: $status ($((retries+1))/$MAX_RETRIES)"
    sleep 5
    retries=$((retries+1))
done

if [ $retries -ge $MAX_RETRIES ]; then
    echo "❌ [$TARGET_ENV] failed to become healthy. Rolling back!"
    echo "    (Action: Shutting down the broken [$TARGET_ENV] container. [$ACTIVE_ENV] is still serving traffic normally.)"
    docker compose stop $TARGET_ENV
    exit 1
fi

# Nginx 트래픽 스위칭 (무중단)
echo "🚦 Switching Nginx traffic from [$ACTIVE_ENV] to [$TARGET_ENV]..."

cat <<EOF > ./nginx-conf/default.conf
server {
    listen 80;
    location / {
        proxy_pass http://$TARGET_ENV:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Nginx 환경설정 리로드 (reload는 세션을 끊지 않고 우아하게 재적용합니다)
docker compose exec nginx nginx -s reload

echo "✅ Traffic successfully switched to [$TARGET_ENV]!"

# 이전 레거시 컨테이너 중지
echo "🛑 Stopping the old container [$ACTIVE_ENV]..."
docker compose stop $ACTIVE_ENV

echo "🎉 Deployment Completed Automatically and Safely!"
