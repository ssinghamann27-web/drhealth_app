#!/bin/bash
echo "🚀 Starting DrHealth AI Backend on Render..."
uvicorn lib.ai_model.server_fastapi:app --host=0.0.0.0 --port=\
