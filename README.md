# 📘 Aurora Applied AI/ML Engineer — Question Answering Service

This repository contains my implementation of the Aurora Applied AI/ML Engineer Take-Home Assignment.

The goal is to build a small API service that can answer natural-language questions about member messages retrieved from Aurora’s public /messages/ API. The service uses semantic search with embeddings to find the most relevant messages and generate concise answers.

🌟 Features
✅ Semantic Retrieval (Embeddings)

Uses SentenceTransformer all-MiniLM-L6-v2

Converts each message into an embedding vector

Computes cosine similarity with the user’s question

Retrieves the most relevant message(s)

✅ Automatic Local Fallback Dataset

If the remote API is unavailable (e.g., returns HTTP 402 Payment Required), the service:

Logs the failure

Loads a local fallback dataset (sample_messages.json)

Builds embeddings from that dataset

➡️ This guarantees that /ask always works, even when the public API fails.

✅ FastAPI Backend

/ask — question-answering endpoint

/health — diagnostic endpoint

Full interactive API docs at /docs

✅ Docker Support

Production-ready Dockerfile

Works on any container platform (Render, Cloud Run, etc.)

## 🔗 Live Deployed Service (Render)

Your service is deployed and publicly accessible:

👉 https://aurora-qa-service-1.onrender.com

Swagger Docs

👉 https://aurora-qa-service-1.onrender.com/docs

Test Endpoint

POST /ask
Example body:

{
  "question": "When is Layla planning her trip to London?"
}

## 🗂️ Repository Structure
.
├── main.py
├── requirements.txt
├── Dockerfile
├── sample_messages.json
├── .gitignore
└── README.md

## 🚀 Architecture Overview
1️⃣ Message Loading (Startup)

On startup, the service attempts to fetch messages from:

GET https://november7-730026606190.europe-west1.run.app/messages/


It uses pagination (skip, limit) to load all items.

If any HTTP or network error occurs — including the frequent:

HTTP 402 Payment Required


the service:

Wraps the call in try/except

Logs the exact error

Loads sample_messages.json

Continues running normally

This ensures the application never breaks.

2️⃣ Embedding & Indexing

Each message is converted into:

"{user_name} {timestamp} {message}"


Then:

Embedded using all-MiniLM-L6-v2

Stored in a NumPy embedding matrix

Used during query-time semantic search

If embeddings fail to load, a keyword fallback is used.

3️⃣ Question Answering Logic

When a client calls /ask:

The question is embedded

Cosine similarity is computed

Top-k most relevant messages are selected

The best match is formatted as:

"{user_name} [timestamp]: {message}"


If no relevant message exists:

"I couldn’t find that information in the member messages."

## 🧪 API Endpoints
▶ POST /ask

Request

{
  "question": "When is Layla planning her trip to London?"
}


Response

{
  "answer": "Layla [2024-01-01T10:00:00Z]: I'm planning a trip to London in March."
}

▶ GET /health

Example

{
  "status": "ok",
  "messages_loaded": 3
}


If the remote API fails (e.g., 402), you will see the local dataset count.

## ⚠ Handling HTTP 402 Payment Required

During testing, the public API frequently returned:

402 Payment Required


To ensure reliability, the service intentionally:

Wraps all remote requests in try/except

Catches all httpx errors (402, 403, 404, timeouts, etc.)

Logs the failure

Loads sample_messages.json

Still answers questions normally

If Aurora restores public access, the service will automatically switch back to live messages.

## 📂 Local Fallback Dataset (sample_messages.json)

A small dataset mimicking the remote schema:

{
  "total": 3,
  "items": [
    {
      "id": "1",
      "user_id": "layla",
      "user_name": "Layla",
      "timestamp": "2024-01-01T10:00:00Z",
      "message": "I'm planning a trip to London in March."
    },
    {
      "id": "2",
      "user_id": "vikram",
      "user_name": "Vikram Desai",
      "timestamp": "2024-01-02T09:30:00Z",
      "message": "I currently own two cars."
    },
    {
      "id": "3",
      "user_id": "amira",
      "user_name": "Amira",
      "timestamp": "2024-01-03T18:45:00Z",
      "message": "My favorite restaurants are Noma, Osteria Francescana, and a small ramen place near home."
    }
  ]
}


Supports all example question types.

## 🏃 Running the Service Locally
1. Clone the repository
git clone https://github.com/<your-username>/aurora-qa-service.git
cd aurora-qa-service

2. Create & activate a virtual environment

Windows

python -m venv venv
venv\Scripts\activate


macOS / Linux

python3 -m venv venv
source venv/bin/activate

3. Install dependencies
pip install -r requirements.txt

4. Run the API
uvicorn main:app --reload


Access:

Swagger UI → http://127.0.0.1:8000/docs

Health → http://127.0.0.1:8000/health

Ask → http://127.0.0.1:8000/ask

## 🐳 Running with Docker
Build image
docker build -t aurora-qa-service .

Run container
docker run -p 8000:8000 aurora-qa-service

## 🚀 Deployment (Render Instructions Used)

(Keep this short — they just need to know you deployed correctly)

Login to Render

Create a Web Service → Docker

Connect GitHub repo

Use default build settings

Render automatically builds & deploys

Service runs on port 8000 (Render auto-detects from Uvicorn)

## 📊 Design Notes (Bonus)
Why embeddings?

Handles paraphrasing

Captures meaning, not just keywords

Lightweight & fast

No external LLM/API required

Alternative approaches considered
Approach	                      Pros	                        Cons
Keyword Search	           Very simple	                Poor semantic understanding
Embeddings (Chosen)	       Accurate, low-cost, fast	    Returns original message, not generated text
RAG + LLM	                 Best natural answers	        Requires external LLM API + cost

## 📈 Data Insights (Bonus)

If full production data were available, I would examine:

Missing timestamps or user names

Duplicate IDs

Contradictory member information

PII handling and anonymization

Message topic clusters & activity patterns

## 🔧 Adapting the Service

To point the service to a new messages API:

Update MESSAGES_URL in main.py

Ensure the API returns:

{
  "total": <int>,
  "items": [
    { "id", "user_id", "user_name", "timestamp", "message" }
  ]
}


Optionally update sample_messages.json

No other code changes required.

## 📌 API Reference
POST /ask

Request:

{
  "question": "your question here"
}


Response:

{
  "answer": "..."
}



## 🚀 Submission

As requested in the assessment instructions, the following items complete the submission:

1. Public GitHub Repository

Your implementation is available publicly at:
👉 https://github.com/rahul-datalab/aurora-qa-service

2. Deployed Service URL

The FastAPI service is deployed on Render:
👉 https://aurora-qa-service-1.onrender.com

3. Example API Endpoint

Ask endpoint:

POST https://aurora-qa-service-1.onrender.com/ask


Example request:

{
  "question": "When is Layla planning her trip to London?"
}


Example response:

{
  "answer": "Layla (2024-01-01T10:00:00Z): I'm planning a trip to London in March 2025."
}
