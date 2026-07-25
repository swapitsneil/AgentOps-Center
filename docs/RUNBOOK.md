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

---

## Standalone Cloud SigNoz MCP Deployment (Render)

Deploy the official SigNoz MCP Server as an independent Web Service on Render:

1. **New Web Service** -> **Deploy an existing image**: `signoz/signoz-mcp-server:latest`
2. **Environment Variables**:
   - `TRANSPORT_MODE`: `http`
   - `MCP_SERVER_PORT`: `10000`
   - `MCP_SERVER_HOST`: `0.0.0.0`
   - `SIGNOZ_URL`: `https://us.signoz.cloud` (or self-hosted query service API URL)
   - `SIGNOZ_API_KEY`: `<your-signoz-api-key>`
3. **Connect Backend**:
   - Set `SIGNOZ_MCP_URL` = `http://agentops-signoz-mcp:10000/mcp` (or public HTTPS URL) on `agentops-center-backend`.
