# AgentOps Center Operations Runbook

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
