#!/bin/bash
# FinTalk Feishu Bot — auto-restart wrapper
# Usage: nohup bash run_feishu_bot.sh > feishu_bot.log 2>&1 &

export FEISHU_APP_ID="${FEISHU_APP_ID:-cli_a9466001417a9cd2}"
export FEISHU_APP_SECRET="${FEISHU_APP_SECRET}"
export DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY}"

cd "$(dirname "$0")"
source .venv/bin/activate

while true; do
    echo "[$(date)] Starting FinTalk Feishu Bot..."
    python feishu_bot.py
    EXIT_CODE=$?
    echo "[$(date)] Bot exited with code $EXIT_CODE, restarting in 5s..."
    sleep 5
done
