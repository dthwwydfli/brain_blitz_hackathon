"""CityPulse backend — FastAPI + CopilotKit AG-UI endpoint.

Agent name `citypulse_agent` must match the frontend `useCoAgent({ name })`.
Verified API (copilotkit 0.1.94): CopilotKitRemoteEndpoint + LangGraphAGUIAgent.
"""
import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from copilotkit import CopilotKitRemoteEndpoint, LangGraphAGUIAgent
from copilotkit.integrations.fastapi import add_fastapi_endpoint

from agent.graph import build_graph
from services.redis_service import RedisService

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = LangGraphAGUIAgent(
    name="citypulse_agent",
    graph=build_graph(),
    description="Infrastructure risk intelligence agent",
)
endpoint = CopilotKitRemoteEndpoint(agents=[agent])
add_fastapi_endpoint(app, endpoint, "/copilotkit")


@app.get("/health")
async def health():
    redis_ok = await RedisService().health_check()
    return {
        "status": "ok",
        "redis": "connected" if redis_ok else "disconnected",
        "version": "1.0.0",
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
