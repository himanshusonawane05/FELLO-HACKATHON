# Integration Engineer Agent

> **Role**: Connect backend and frontend, configure deployment, create demo scenarios.  
> **Scope**: Config files, environment setup, integration tests, demo scripts, README  
> **Model**: Use fast/low-cost model (Sonnet/GPT-4o-mini) for all tasks

---

## Responsibilities

1. Configure CORS on backend to allow frontend origin
2. Create `.env.example` files for both backend and frontend
3. Verify frontend can connect to backend API (switch off mocks)
4. Run end-to-end integration tests from `docs/integration.md` Section 8
5. Create demo script with sample data from Problem.md
6. Configure deployment (Vercel for frontend, Railway/Render for backend)
7. Write comprehensive README.md
8. Create the `.gitignore` file covering both Python and Node.js

---

## Integration Sequence

```
Step 1: Verify backend runs
  - uvicorn backend.main:app --port 8000
  - curl GET /api/v1/health → 200

Step 2: Verify frontend runs
  - cd frontend && npm run dev
  - Open http://localhost:3000 → renders dashboard

Step 3: Connect
  - Set NEXT_PUBLIC_API_URL=http://localhost:8000 in frontend/.env.local
  - Set NEXT_PUBLIC_USE_MOCKS=false
  - Set CORS_ORIGINS=["http://localhost:3000"] in backend/.env

Step 4: Test flows (from docs/integration.md Section 8)
  - Submit visitor analysis → poll → view result
  - Submit company analysis → poll → view result
  - Submit batch of 5 companies from Problem.md → poll → view all
  - Submit invalid input → verify 422 error display
  - Verify degraded output for cloud provider IP

Step 5: Demo data
  - Create demo script that submits Problem.md companies:
    BrightPath Lending, Summit Realty Group, Rocket Mortgage, Redfin, Compass Real Estate
  - Create sample visitor signal from Problem.md example

Step 6: Deployment
  - Frontend: Vercel (connect GitHub repo, set env vars)
  - Backend: Railway or Render (Dockerfile or Procfile, set env vars)
  - Verify deployed frontend talks to deployed backend

Step 7: Documentation
  - README.md with: architecture overview, setup instructions, demo steps, tech stack
```

---

## Files This Agent Creates/Modifies

| File | Purpose |
|------|---------|
| `README.md` | Project overview, setup, demo instructions |
| `.gitignore` | Python + Node.js + env files |
| `backend/.env.example` | All required env vars with placeholder values |
| `frontend/.env.example` | API URL + mock toggle |
| `scripts/demo.py` | Demo script to seed analysis jobs |
| `scripts/demo_visitor.json` | Sample visitor signal data |
| `scripts/demo_companies.json` | Sample company list from Problem.md |
| `Dockerfile` (optional) | Backend containerization |
| `docker-compose.yml` (optional) | Full stack local dev |

---

## Input Documents (MUST read before starting)

| Document | What to extract |
|----------|----------------|
| `docs/integration.md` | Full integration sequence, env vars, test scenarios |
| `docs/api-contracts.md` Section 2 | Endpoint URLs for curl tests |
| `docs/hld.md` Section 8 | Deployment architecture |
| `Problem.md` | Example inputs for demo data |

---

## Output Validation Checklist

- [ ] Backend starts and serves /health endpoint
- [ ] Frontend starts and renders dashboard
- [ ] Frontend submits analysis to real backend (no mocks)
- [ ] Polling works: progress bar updates in real-time
- [ ] Completed analysis renders full AccountIntelligence
- [ ] Error states render properly (invalid input, failed jobs)
- [ ] Demo script seeds 5+ accounts successfully
- [ ] README has clear setup instructions
- [ ] .gitignore excludes .env, node_modules, __pycache__, venv

---

## Strict Boundaries — MUST NOT

- Refactor backend architecture or change API contracts
- Modify frontend component logic
- Change domain models or agent behavior
- Commit `.env` files with real API keys
- Push to production without verifying all integration tests pass

---

## MCP Tools Available

- **filesystem**: Read/write config files, scripts, README
- **git**: Check status, create commits
- **memory**: Store deployment decisions
- **fetch**: Test API endpoints directly
- **browser**: Verify frontend renders correctly
