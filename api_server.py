"""
HTTP bridge for Nexus -- exposes ExecutionGateway over HTTP so the MCIS
Node.js backend can call browser/desktop/office actions.

Add this file to the root of the nexus repo, then:
    pip install fastapi uvicorn
    python api_server.py

This starts a local server at http://localhost:8000
"""
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from execution_gateway import ExecutionGateway

app = FastAPI(title="Nexus Execution API")

# One shared gateway instance -- keeps the browser session alive between
# calls instead of relaunching a browser for every single action (much
# faster). Note: this is a single, shared instance -- see the note in
# README-integration.md about not sending concurrent /execute requests.
gateway = ExecutionGateway()


class ActionRequest(BaseModel):
    platform: str  # "desktop" or "browser"
    action: str
    parameters: dict[str, Any] = {}
    target: dict[str, Any] = {}
    value: Optional[Any] = None
    approval_token: Optional[str] = None


@app.post("/execute")
def execute_action(req: ActionRequest):
    try:
        result = gateway.execute(req.model_dump())
        return {
            "success": result.success,
            "platform": result.platform,
            "action": result.action,
            "message": getattr(result, "message", None),
            "data": getattr(result, "data", None),
            "error": getattr(result, "error", None),
            "evidence": getattr(result, "evidence", None),
        }
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
