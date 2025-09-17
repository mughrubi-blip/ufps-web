from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from io import BytesIO

# === IMPORT YOUR COMPLETED UFPS ENGINE HERE ===
# Replace this line with the real import
# It must expose: redact_bytes(data: bytes, filename: str) -> (bytes, str)
from ufps_engine import redact_bytes

app = FastAPI(title="UFPS Web Scanner")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/scan")
async def scan(file: UploadFile = File(...), inline: str = Form("download")):
    raw = await file.read()
    try:
        redacted_bytes, suggested_name = redact_bytes(raw, file.filename)
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

    buf = BytesIO(redacted_bytes)
    disposition = "inline" if inline == "inline" else "attachment"
    headers = {"Content-Disposition": f"{disposition}; filename=\"{suggested_name}\""}
    return StreamingResponse(buf, media_type="application/octet-stream", headers=headers)

@app.get("/healthz")
async def healthz():
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
