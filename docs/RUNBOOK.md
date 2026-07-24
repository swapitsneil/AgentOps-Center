# AgentOps Center Operations Runbook

---

## 🌐 Live Production Links

| Component | Live Production URL | Host | Status |
| :--- | :--- | :--- | :--- |
| **AgentOps Center UI** | 🚀 [https://agent-ops-center-kohl.vercel.app](https://agent-ops-center-kohl.vercel.app/) | **Vercel** | 🟢 Live |
| **Backend Service** | ⚡ [https://agentops-center-backend.onrender.com](https://agentops-center-backend.onrender.com) | **Render** | 🟢 Live |
| **API Documentation** | 📖 [https://agentops-center-backend.onrender.com/docs](https://agentops-center-backend.onrender.com/docs) | **Render** | 🟢 Live |
| **Health Monitor** | 🩺 [https://agentops-center-backend.onrender.com/health](https://agentops-center-backend.onrender.com/health) | **Render** | 🟢 Live |

---

## Local Development Setup

### 1. Prerequisites
- Python >= 3.11
- Node.js >= 18
- Docker & Docker Compose

### 2. Start Backend
```powershell
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Start Frontend
```powershell
cd frontend
npm run dev
```

### 4. Running Verification Tests
```powershell
cd tests
pytest test_workflow.py
```
