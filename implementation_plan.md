# AI Financial Advisor Chatbot — Finalized System Design

> **Stack**: Python · FastAPI · LangGraph · LangChain · React · Docker · PostgreSQL · Redis · ChromaDB

---

## ✅ Decisions Finalized

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Market** | 🇮🇳 India (NSE/BSE/AMFI) | AMFI, NSE open APIs available for free |
| **LLM Strategy** | Ollama (local) + Groq API | Best cost-performance combo |
| **Frontend** | React (Vite) | Modern, fast, job-marketable |
| **Cloud** | Self-hosted via Oracle Free VPS | Always-free, no credit card trap |
| **CI/CD** | GitHub Actions | Better portfolio visibility |
| **Financial Data** | yFinance + AMFI API + NSE tools | 100% open source, no cost |
| **Databases** | PostgreSQL + Redis + ChromaDB | See full breakdown below |

---

## 🧠 LLM Strategy — Full Breakdown

This is the **smartest part** of your architecture. Use the right model for the right task.

```
┌─────────────────────────────────────────────────────────────────┐
│                    LLM ROUTING STRATEGY                          │
│                                                                  │
│  User Query                                                      │
│      │                                                           │
│      ▼                                                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              LangChain LLM Router                        │   │
│  └────────────┬────────────────────────┬─────────────────── ┘   │
│               │                        │                         │
│        SIMPLE TASKS               COMPLEX TASKS                  │
│               │                        │                         │
│               ▼                        ▼                         │
│  ┌─────────────────────┐   ┌───────────────────────────────┐    │
│  │   Ollama (Local)    │   │       Groq API (Cloud)        │    │
│  │                     │   │                               │    │
│  │  Model: Llama 3.2   │   │  Model: Llama 3.1 70B /      │    │
│  │  (3B or 8B)         │   │  Mixtral 8x7B                 │    │
│  │                     │   │                               │    │
│  │  Use for:           │   │  Use for:                     │    │
│  │  • Intent classify  │   │  • Financial analysis         │    │
│  │  • Simple Q&A       │   │  • Complex reasoning          │    │
│  │  • Embeddings       │   │  • Report generation          │    │
│  │  • Summarization    │   │  • Multi-step planning        │    │
│  │  • Data extraction  │   │  • Regulatory interpretation  │    │
│  │                     │   │                               │    │
│  │  Cost: FREE ✅      │   │  Cost: Near-free ✅           │    │
│  │  Speed: Medium      │   │  Speed: Fastest LLM API 🚀    │    │
│  └─────────────────────┘   └───────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Why Groq?
- **Fastest LLM inference API** in the world (GroqChip hardware)
- **Free tier**: 14,400 requests/day on Llama 3.1 70B
- LangChain has native `ChatGroq` support — plug & play
- Much faster than OpenAI for same quality output

### Embedding Models (Always Local — FREE)
```
For RAG embeddings, use HuggingFace models via sentence-transformers:

Option 1: BAAI/bge-m3       → Best multilingual (handles Hindi terms)
Option 2: all-MiniLM-L6-v2  → Fast, lightweight, English-only
Option 3: nomic-embed-text   → Via Ollama, local, strong quality

Recommendation: BAAI/bge-m3 (handles ₹, %, Indian financial terms)
```

### LangChain Code Pattern
```python
from langchain_community.chat_models import ChatOllama
from langchain_groq import ChatGroq

# For simple tasks
local_llm = ChatOllama(model="llama3.2:3b", base_url="http://ollama:11434")

# For complex tasks
groq_llm  = ChatGroq(model="llama-3.1-70b-versatile", api_key=GROQ_API_KEY)

# Router in LangGraph node
def route_llm(state: AgentState):
    complexity = classify_query_complexity(state["query"])
    return groq_llm if complexity == "high" else local_llm
```

---

## 🗄️ Database Selection — Full Breakdown

```
┌───────────────────────────────────────────────────────────────────────┐
│                      DATABASE ARCHITECTURE                            │
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  ┌──────────┐  │
│  │  PostgreSQL  │  │    Redis     │  │  ChromaDB   │  │  SQLite  │  │
│  │              │  │              │  │             │  │          │  │
│  │ Primary DB   │  │ Cache +      │  │ Vector DB   │  │ Dev/Test │  │
│  │              │  │ Session +    │  │ for RAG     │  │ only     │  │
│  │ Stores:      │  │ Broker       │  │             │  │          │  │
│  │ • Users      │  │              │  │ Stores:     │  │ Fast     │  │
│  │ • Chats      │  │ Stores:      │  │ • Doc chunks│  │ local    │  │
│  │ • Messages   │  │ • JWT tokens │  │ • Embeddings│  │ testing  │  │
│  │ • Documents  │  │ • API cache  │  │ • Metadata  │  │ no setup │  │
│  │ • Audit logs │  │ • Rate limit │  │             │  │ needed   │  │
│  │              │  │ • Chat mem   │  │ Free &      │  │          │  │
│  │ Free: ✅     │  │ • Task queue │  │ open-source │  │          │  │
│  └──────────────┘  └──────────────┘  └─────────────┘  └──────────┘  │
└───────────────────────────────────────────────────────────────────────┘
```

### Database Decision Guide

#### 1. 🐘 PostgreSQL — Primary Database
```
What it stores:  Users, conversations, messages, document metadata, audit logs
Why PostgreSQL:
  ✅ JSONB columns (store flexible metadata without extra tables)
  ✅ Full-text search built-in (search old conversations)
  ✅ ACID transactions (critical for financial data)
  ✅ Used by 90% of fintech companies
  ✅ pgAdmin UI for easy management
  
Docker Image: postgres:16-alpine
```

#### 2. ⚡ Redis — Cache + Session + Message Broker
```
What it stores:  JWT token blacklist, API response cache, chat memory, task queue
Why Redis:
  ✅ Sub-millisecond reads (market data caching)
  ✅ TTL expiry (auto-expire cached stock prices after 5 mins)
  ✅ Pub/Sub for events between microservices
  ✅ Used as Celery broker for async tasks
  ✅ LangChain RedisChatMessageHistory for conversation memory

Docker Image: redis:7-alpine
```

#### 3. 🔍 ChromaDB — Vector Database for RAG
```
What it stores:  Document embeddings (SEBI PDFs, financial guides, fund data)
Why ChromaDB:
  ✅ 100% open source, runs locally in Docker
  ✅ LangChain native integration
  ✅ No cloud account needed
  ✅ Persistent mode stores data on disk
  ✅ Can migrate to Qdrant later (same API pattern)

Docker Image: chromadb/chroma:latest
Migration path: ChromaDB (dev) → Qdrant (prod, when scale needed)
```

#### 4. 🗃️ SQLite — Development & Testing Only
```
What it stores:  Temporary test data during unit tests
Why SQLite:
  ✅ Zero setup — file-based
  ✅ pytest uses it for fast test isolation
  ✅ SQLAlchemy supports it out of the box
  ❌ Never use in production
```

---

## 🌍 Cloud Deployment — Open Source / Free Tier Options

### Option A: Oracle Cloud Free Tier ⭐ (BEST for self-hosted)
```
What you get FREE forever:
  • 2x AMD VMs (1 OCPU, 1GB RAM each)
  • 4x ARM VMs (24GB RAM total!) ← Run everything here
  • 200GB block storage
  • 10TB outbound bandwidth/month

Perfect for: Running all Docker containers on ARM instances
Cost: $0 forever (no credit card auto-charge)
Setup: Install Docker + Docker Compose → deploy
URL: cloud.oracle.com/free
```

### Option B: Railway.app (Easiest to start)
```
Free tier: $5 credit/month (enough for dev testing)
Supports: Docker containers directly
Best for: Quick demo deployment, sharing with others
Limitation: Sleeps after inactivity on free tier
```

### Option C: Fly.io (Great for microservices)
```
Free tier: 3 shared VMs, 3GB storage
Supports: Docker containers, global edge network
Best for: Low-latency deployments
CLI-based deployment: flyctl deploy
```

### Option D: Coolify on VPS (Self-hosted Heroku)
```
What it is: Open-source PaaS you install on any VPS
Cost: Free software + cost of VPS (~$5/month DigitalOcean)
Features: Automatic SSL, GitHub integration, one-click deploys
Best for: Full control with easy management UI
```

### 📋 Recommendation by Phase
```
Phase 1 (Development):  Local Docker Compose — zero cost
Phase 2 (Demo/Testing): Railway or Fly.io — free tier
Phase 3 (Production):   Oracle Cloud Free Tier ARM VMs + Coolify
```

---

## ⚙️ GitHub Actions vs GitLab CI — Final Answer

### Choose GitHub Actions ✅

| Factor | GitHub Actions | GitLab CI |
|--------|---------------|-----------|
| **Portfolio visibility** | ⭐⭐⭐⭐⭐ Public repos visible to recruiters | ⭐⭐⭐ Less discoverable |
| **Marketplace** | 15,000+ pre-built actions | Fewer integrations |
| **Free minutes** | 2,000 min/month (public: unlimited) | 400 min/month |
| **Container Registry** | GitHub Container Registry (GHCR) free | GitLab Registry free |
| **Learning curve** | Easy YAML, great docs | Slightly steeper |
| **Job market** | Most companies use GitHub | GitLab popular in enterprise |
| **Community** | Much larger community | Smaller |

> **Verdict**: Use **GitHub + GitHub Actions**. Your portfolio on GitHub gets seen by recruiters. GitLab is better for enterprises with complex DevSecOps — not needed at this stage.

---

## 📈 Financial Data Sources (India, Open Source)

### Live Market Data
```python
# 1. yFinance — Stocks, Indices (NSE/BSE)
import yfinance as yf
stock = yf.Ticker("RELIANCE.NS")  # .NS suffix for NSE
stock = yf.Ticker("RELIANCE.BO")  # .BO suffix for BSE

# What you get: OHLCV, P/E, dividends, financials, news
# Cost: FREE, no API key needed
```

### Mutual Fund Data
```python
# 2. AMFI India API — Official Mutual Fund NAV
# URL: https://www.amfiindia.com/spages/NAVAll.txt
# All NAVs updated daily, completely free

# 3. mfapi.in — Unofficial but excellent MF API
import httpx
response = await httpx.get("https://api.mfapi.in/mf/120503")
# Returns full NAV history for any fund scheme
```

### Financial News
```python
# 4. RSS Feeds (Free)
feeds = [
    "https://economictimes.indiatimes.com/markets/rss.cms",
    "https://www.moneycontrol.com/rss/MCtopnews.xml",
    "https://www.livemint.com/rss/markets",
]

# 5. yFinance news (already included)
news = yf.Ticker("NIFTY50.NS").news
```

### Regulatory/Knowledge Data (for RAG)
```
• SEBI regulations: sebi.gov.in (PDFs, free download)
• RBI guidelines: rbi.org.in (master circulars, free)
• Income Tax: incometax.gov.in (guides, FAQs)
• AMFI investor education PDFs
```

---

## 🔄 Updated CI/CD Pipeline

### CI — `.github/workflows/ci.yml`
```yaml
name: CI Pipeline
on:
  push:
    branches: [main, develop, 'feature/**']
  pull_request:
    branches: [main, develop]

jobs:
  code-quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with: {python-version: '3.12'}
      - run: pip install ruff black mypy bandit
      - run: ruff check ./services
      - run: black --check ./services
      - run: bandit -r ./services -ll

  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [auth-service, agent-service, rag-service, market-data-service]
    steps:
      - uses: actions/checkout@v4
      - name: Run tests for ${{ matrix.service }}
        run: |
          cd services/${{ matrix.service }}
          pip install -r requirements.txt -r requirements-dev.txt
          pytest tests/ --cov=app --cov-report=xml --cov-fail-under=75

  build-images:
    needs: [code-quality, test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build all Docker images
        run: docker compose build

  security-scan:
    needs: build-images
    runs-on: ubuntu-latest
    steps:
      - name: Trivy vulnerability scan
        uses: aquasecurity/trivy-action@master
```

### CD — `.github/workflows/cd.yml`
```yaml
name: CD Pipeline
on:
  push:
    branches: [main]

jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      - name: Push to GHCR
        run: |
          echo ${{ secrets.GITHUB_TOKEN }} | docker login ghcr.io -u $GITHUB_ACTOR --password-stdin
          docker compose build
          docker compose push
      - name: Deploy to Staging VPS
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.STAGING_HOST }}
          username: ubuntu
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /app/ai-financial-advisor
            docker compose pull
            docker compose up -d
            sleep 10
            curl -f http://localhost:8002/health || exit 1

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production  # ← Requires manual approval in GitHub
    steps:
      - name: Deploy to Production
        uses: appleboy/ssh-action@v1
        # ... same as staging with prod secrets
```

---

## 🗺️ Final Architecture Diagram (Updated)

```
CLIENT LAYER
─────────────────────────────────────────────────
React (Vite) Chat UI
       │
       ▼ HTTPS
GATEWAY LAYER
─────────────────────────────────────────────────
Nginx (reverse proxy + rate limiting + SSL)
       │
       ├──────────────────────────────────┐
       ▼                                  ▼
SERVICES LAYER
─────────────────────────────────────────────────
┌────────────┐  ┌──────────────────────────┐
│  FastAPI   │  │  FastAPI Agent Service   │
│  Auth Svc  │  │  (LangGraph)             │
│  :8001     │  │  :8002                   │
└────────────┘  │                          │
                │  ┌────────┐ ┌─────────┐  │
                │  │ Ollama │ │  Groq   │  │
                │  │(local) │ │  API    │  │
                │  └────────┘ └─────────┘  │
                └──────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
┌──────────────┐ ┌─────────────┐ ┌────────────────┐
│FastAPI RAG   │ │FastAPI Mkt  │ │ Notification   │
│Service :8003 │ │Data  :8004  │ │ Service :8005  │
│              │ │             │ │ (Phase 2)      │
│ChromaDB +    │ │yFinance +   │ │                │
│HuggingFace   │ │AMFI + NSE   │ │                │
│Embeddings    │ │RSS Feeds    │ │                │
└──────────────┘ └─────────────┘ └────────────────┘

DATA LAYER
─────────────────────────────────────────────────
PostgreSQL:5432  │  Redis:6379  │  ChromaDB:8000
(Users/Chats)    │  (Cache/     │  (Embeddings/
                 │   Sessions/  │   RAG Docs)
                 │   Broker)    │

OBSERVABILITY
─────────────────────────────────────────────────
Prometheus → Grafana   │   Loki (logs)
```

---

## 🚀 Build Order (Start Here)

```
Week 1-2: Foundation
  1. GitHub repo setup + folder structure
  2. docker-compose.yml with all services defined
  3. PostgreSQL + Redis + ChromaDB running in Docker
  4. auth-service (register, login, JWT)

Week 3-4: Core Agent
  5. agent-service skeleton (FastAPI + WebSocket)
  6. LangGraph single agent with tool routing
  7. Ollama setup (local) + Groq API integration
  8. Basic RAG pipeline (ingest SEBI PDFs → ChromaDB)

Week 5-6: Data Services
  9. market-data-service (yFinance + AMFI NAV)
  10. Connect agent tools to market data + RAG
  11. React frontend with chat UI

Week 7-8: CI/CD + Polish
  12. GitHub Actions CI pipeline
  13. Deploy to Oracle Free VPS
  14. GitHub Actions CD pipeline
  15. Prometheus + Grafana monitoring
```

---

## 📦 Key Packages Per Service

```toml
# agent-service requirements.txt
fastapi==0.115.0
uvicorn[standard]==0.30.0
langgraph==0.2.0
langchain==0.3.0
langchain-groq==0.2.0
langchain-community==0.3.0   # ChatOllama
langchain-chroma==0.1.4
sentence-transformers==3.0.0  # HuggingFace embeddings
redis==5.0.0
websockets==12.0
pydantic-settings==2.5.0
structlog==24.0.0

# auth-service requirements.txt
fastapi==0.115.0
uvicorn[standard]==0.30.0
sqlalchemy==2.0.0
asyncpg==0.29.0
alembic==1.13.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
pydantic-settings==2.5.0

# market-data-service requirements.txt
fastapi==0.115.0
uvicorn[standard]==0.30.0
yfinance==0.2.40
httpx==0.27.0
redis==5.0.0
feedparser==6.0.11           # RSS news feeds
pydantic-settings==2.5.0
```
