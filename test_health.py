#!/usr/bin/env python3
"""
Test script to verify health check endpoint works
"""

import asyncio
import uvicorn
from fastapi import FastAPI

# Create FastAPI app for health checks
app = FastAPI(title="Nintendo Deals Bot", version="1.0.0")

@app.get("/health")
async def health_check():
    """Health check endpoint for Render"""
    return {"status": "healthy", "service": "nintendo-deals-bot"}

async def test_web_server():
    """Test web server"""
    print("🚀 Starting health check server on http://localhost:8000")
    print("📊 Health check endpoint: http://localhost:8000/health")
    print("⏹️  Press Ctrl+C to stop")

    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(test_web_server())
