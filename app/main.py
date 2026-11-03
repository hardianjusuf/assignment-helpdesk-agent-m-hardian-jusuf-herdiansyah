"""
Entry point aplikasi FastAPI — IT Helpdesk Assistant.

Alur endpoint utama:
  1. Menerima pertanyaan/permintaan dari user
  2. Meneruskan ke router (router.py) untuk menentukan intent
  3. Router memanggil RAG (rag.py) atau tool (tools.py) sesuai intent
  4. Mengembalikan response terstruktur ke client
"""

from fastapi import FastAPI
from pydantic import BaseModel

from app.router import handle_query

app = FastAPI(title="IT Helpdesk Assistant API")


class AskRequest(BaseModel):
    query: str


class AskResponse(BaseModel):
    status: str
    intent: str
    data: str


@app.get("/health")
async def health():
    """Endpoint sederhana untuk memastikan service berjalan."""
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest):
    try:
        result = await handle_query(request.query)
        return AskResponse(**result)
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        return {
            "status": "error",
            "intent": "unknown",
            "data": "Maaf, terjadi kesalahan saat memproses permintaan Anda",
        }
