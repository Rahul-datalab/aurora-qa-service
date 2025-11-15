from typing import List, Dict, Any, Optional

import httpx
import numpy as np
import re
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from pathlib import Path
import json
from typing import Optional


# Public API from the assignment
MESSAGES_URL = "https://november7-730026606190.europe-west1.run.app/messages/"

app = FastAPI(title="Aurora AI/ML QA Service")

# Globals
MESSAGES: List[Dict[str, Any]] = []
MESSAGE_TEXTS: List[str] = []
EMBEDDING_MODEL: Optional[SentenceTransformer] = None
MESSAGE_EMBEDDINGS: Optional[np.ndarray] = None


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str


def message_to_text(msg: Dict[str, Any]) -> str:
    """
    Convert one Message object into a text blob we can index.

    Message schema from Swagger:
    {
      "id": "string",
      "user_id": "string",
      "user_name": "string",
      "timestamp": "string",
      "message": "string"
    }
    """
    user_name = msg.get("user_name") or ""
    timestamp = msg.get("timestamp") or ""
    text = msg.get("message") or ""

    # Example: "Layla [2024-01-01T10:00:00Z] Planning a trip to London in March..."
    parts = [user_name, timestamp, text]
    return " ".join(p for p in parts if p)


@app.on_event("startup")
async def load_messages() -> None:
    """
    Try to load messages from the public API. If that fails (e.g. HTTP 402),
    fall back to a local sample dataset so the service remains demo-able.
    """
    global MESSAGES, MESSAGE_TEXTS, EMBEDDING_MODEL, MESSAGE_EMBEDDINGS

    all_items: List[Dict[str, Any]] = []

    # 1) Try remote API
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            skip = 0
            limit = 100
            total: Optional[int] = None

            while True:
                resp = await client.get(
                    MESSAGES_URL,
                    params={"skip": skip, "limit": limit},
                )
                resp.raise_for_status()  # will raise on 4xx/5xx

                data = resp.json()
                page_total = data.get("total")
                items = data.get("items", [])

                if total is None:
                    total = page_total

                if not items:
                    break

                all_items.extend(items)
                skip += len(items)

                if total is not None and len(all_items) >= total:
                    break

        print(f"Loaded {len(all_items)} messages from remote API.")

    except httpx.HTTPError as e:
        # 2) Fallback to local sample data
        print(f"HTTP error while fetching messages: {e}. Using local sample_messages.json.")
        sample_path = Path(__file__).parent / "sample_messages.json"
        if sample_path.exists():
            with sample_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            all_items = data.get("items", [])
            print(f"Loaded {len(all_items)} messages from local sample dataset.")
        else:
            print("sample_messages.json not found. Starting with empty dataset.")

    MESSAGES = all_items
    MESSAGE_TEXTS = [message_to_text(m) for m in MESSAGES]

    if MESSAGES:
        EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        MESSAGE_EMBEDDINGS = EMBEDDING_MODEL.encode(
            MESSAGE_TEXTS,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        print("Built embeddings for messages.")
    else:
        EMBEDDING_MODEL = None
        MESSAGE_EMBEDDINGS = None
        print("No messages available; semantic retrieval will fall back to keyword search.")




def simple_retrieve(question: str, k: int = 3) -> List[Dict[str, Any]]:
    """
    Fallback keyword-based retrieval in case embeddings aren’t ready.
    """
    if not MESSAGES:
        return []

    q = question.lower()
    q_words = [w for w in re.split(r"\W+", q) if w]

    scored: List[tuple[float, Dict[str, Any]]] = []

    for msg, text in zip(MESSAGES, MESSAGE_TEXTS):
        t = text.lower()
        if not t:
            continue
        score = sum(1 for w in q_words if w in t)
        if score > 0:
            scored.append((score, msg))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [m for _, m in scored[:k]]


def semantic_retrieve(question: str, k: int = 3) -> List[Dict[str, Any]]:
    """
    Embeddings-based retrieval using cosine similarity.
    """
    if EMBEDDING_MODEL is None or MESSAGE_EMBEDDINGS is None or not MESSAGE_TEXTS:
        return simple_retrieve(question, k=k)

    q_embedding = EMBEDDING_MODEL.encode([question], convert_to_numpy=True)[0]

    dot = MESSAGE_EMBEDDINGS @ q_embedding
    msg_norms = np.linalg.norm(MESSAGE_EMBEDDINGS, axis=1)
    q_norm = np.linalg.norm(q_embedding)
    sims = dot / (msg_norms * q_norm + 1e-8)

    top_indices = np.argsort(-sims)[:k]
    results: List[Dict[str, Any]] = []
    for idx in top_indices:
        if sims[idx] <= 0:
            continue
        results.append(MESSAGES[idx])
    return results


def format_answer(question: str, candidates: List[Dict[str, Any]]) -> str:
    """
    For now: return the text of the top message, nicely formatted.
    """
    if not candidates:
        return "I couldn’t find that information in the member messages."

    top_msg = candidates[0]
    user_name = top_msg.get("user_name") or ""
    timestamp = top_msg.get("timestamp") or ""
    msg_text = top_msg.get("message") or message_to_text(top_msg)

    if len(msg_text) > 400:
        msg_text = msg_text[:400] + "..."

    meta_parts = []
    if user_name:
        meta_parts.append(user_name)
    if timestamp:
        meta_parts.append(f"({timestamp})")

    if meta_parts:
        meta = " ".join(meta_parts)
        return f"{meta}: {msg_text}"
    else:
        return msg_text


@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest) -> AskResponse:
    """
    Accept a natural-language question and return an answer inferred from messages.
    """
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question must not be empty.")

    candidates = semantic_retrieve(question)
    answer = format_answer(question, candidates)
    return AskResponse(answer=answer)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "messages_loaded": len(MESSAGES),
    }
