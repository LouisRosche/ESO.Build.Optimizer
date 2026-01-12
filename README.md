# ESO Build Optimizer

Combat metrics with ML-powered recommendations for Elder Scrolls Online.

**"You performed at X percentile. To improve your contribution, do Y."**

---

## For Players

### Quick Start

1. **Install the Addon**
   - Use [Minion](https://minion.mmoui.com/) (recommended): Search "ESO Build Optimizer" → Install
   - Or download from [ESOUI.com](https://www.esoui.com/) → Extract to `Documents/Elder Scrolls Online/live/AddOns/`

2. **Create an Account**
   - Visit the website and register with email/password
   - In-game, type: `/ebo link <token>` (token shown on website)

3. **Play Normally**
   - The addon tracks your combat automatically
   - Optional: Small UI shows real-time DPS/HPS (toggle with `/ebo ui`)

4. **View Your Analytics**
   - Log into the website to see your dashboard
   - Compare your performance against similar players
   - Get gear and skill recommendations

### In-Game Commands

| Command | Description |
|---------|-------------|
| `/ebo` | Show help |
| `/ebo ui` | Toggle metrics display |
| `/ebo link <token>` | Link account to website |
| `/ebo reset` | Reset current encounter |

### What Gets Tracked

- **DPS/HPS** - Damage and healing per second
- **Buff Uptime** - How well you maintain buffs
- **Crit Rate** - Critical hit percentage
- **Deaths** - Time spent dead
- **Build Snapshot** - Your gear, skills, and CP at time of combat

---

## For Developers

### Project Structure

```
ESO.Build.Optimizer/
├── addon/                  # Lua addon (ESOUI distribution)
├── companion/              # Desktop sync app (Python)
├── api/                    # FastAPI backend
├── web/                    # React frontend (Vite)
├── ml/                     # ML pipeline
├── data/                   # Feature database (1,981 entries)
├── docs/technical/         # Technical documentation
├── tests/                  # Test suite
└── .github/workflows/      # CI/CD pipeline
```

### Local Development

```bash
# Clone
git clone https://github.com/your-username/ESO.Build.Optimizer.git
cd ESO.Build.Optimizer

# Backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Edit with your settings
uvicorn api.main:app --reload

# Frontend
cd web && npm install && npm run dev

# Tests
python scripts/run_tests.py
```

### Technical Documentation

| Document | Description |
|----------|-------------|
| [ESO Addon API](docs/technical/ESO_ADDON_API.md) | Lua API, events, SavedVariables |
| [FastAPI Best Practices](docs/technical/FASTAPI_BEST_PRACTICES.md) | Backend patterns |
| [React/Vite Guide](docs/technical/REACT_VITE_BEST_PRACTICES.md) | Frontend patterns |
| [Deployment Guide](docs/technical/DEPLOYMENT_FREE_TIER.md) | Vercel, Render, Neon |
| [PyInstaller Packaging](docs/technical/PYINSTALLER_PACKAGING.md) | Companion app builds |

### CI/CD Pipeline

GitHub Actions runs on every push:
- Python tests (pytest)
- Frontend tests (vitest, TypeScript, ESLint)
- Lua validation (syntax, luacheck)
- Data validation (JSON integrity)
- Security scan (Bandit)

---

## Deployment (Owner Reference)

### Infrastructure (Free Tier)

| Service | Purpose | Limitations |
|---------|---------|-------------|
| **Vercel** | Frontend hosting | 100GB bandwidth |
| **Render** | Backend API | 750hrs/mo, 15min sleep |
| **Neon** | PostgreSQL | 0.5GB, auto-suspend |

### Quick Deploy

1. **Database**: Create project at [neon.tech](https://neon.tech), copy connection string
2. **Backend**: Connect repo at [render.com](https://render.com), set env vars
3. **Frontend**: Import repo at [vercel.com](https://vercel.com), set `VITE_API_URL`

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | Neon PostgreSQL connection |
| `JWT_SECRET_KEY` | Yes | JWT signing secret |
| `ALLOWED_ORIGINS` | Yes | CORS (your Vercel URL) |

---

## ESOUI Submission

The addon is packaged for ESOUI.com/Minion distribution:

```
ESOBuildOptimizer/
├── ESOBuildOptimizer.txt     # Manifest (CRLF, UTF-8 no BOM)
├── ESOBuildOptimizer.lua     # Main addon
└── modules/                  # Combat, build, UI, advisor
```

**Manifest Compliance:**
- APIVersion: 101046 101047 (Update 46-48)
- AddOnVersion: 1 (integer)
- Event filtering on high-frequency events
- Single namespaced global table

---

## What Makes This Different

| Feature | Combat Metrics | ESO Build Optimizer |
|---------|----------------|---------------------|
| Raw DPS numbers | ✓ | ✓ |
| Percentile ranking | ✗ | ✓ |
| "You're better than X% of similar players" | ✗ | ✓ |
| Actionable recommendations | ✗ | ✓ |
| "Switch X set to Y for +8% DPS" | ✗ | ✓ |
| Cross-character analytics | ✗ | ✓ |
| Historical trends | ✗ | ✓ |

---

## License

Data compiled from publicly available ESO game information for educational and optimization purposes.

---

*Version 1.0.0 | ESO Update 48 | January 2026*
