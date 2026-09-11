from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .analyzer import analyze_password
from .breach import check_hibp
from .models import AnalyzeRequest, AnalyzeResponse

app = FastAPI(
    title="SecureScope API",
    version="0.1.0",
    description="Privacy-first password risk analysis.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    result = analyze_password(request.password, request.context)
    try:
        breached, count = await check_hibp(request.password)
    except Exception as error:
        raise HTTPException(status_code=502, detail="Breach service is temporarily unavailable.") from error

    result.breached = breached
    result.breach_count = count
    if breached:
        result.score = min(result.score, 15)
        result.label = "critical"
        result.findings.insert(0, {
            "code": "breached",
            "severity": "high",
            "title": "Found in known data breaches",
            "detail": "Do not reuse this password. Change it anywhere it was used.",
        })
    return result
