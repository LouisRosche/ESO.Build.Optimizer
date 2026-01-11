# ESO Build Optimizer

An intelligent ESO performance analytics system that tracks combat metrics, analyzes builds, and generates actionable recommendations for Elder Scrolls Online players.

## Project Overview

```
ESO.Build.Optimizer/
├── api/                    # FastAPI backend
├── web/                    # React frontend (Vite)
├── addon/                  # Lua addon for ESO
├── companion/              # Desktop companion app
├── ml/                     # Machine learning pipeline
├── data/                   # Feature database (JSON)
├── scripts/                # Utility scripts
├── docker/                 # Docker configurations
├── render.yaml             # Render.com deployment blueprint
└── requirements.txt        # Python dependencies
```

## Quick Start (Local Development)

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose (optional)
- PostgreSQL 15+ (or use Docker)

### Option 1: Using Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/your-username/ESO.Build.Optimizer.git
cd ESO.Build.Optimizer

# Start all services
docker-compose -f docker/docker-compose.dev.yml up

# API available at: http://localhost:8000
# API docs at: http://localhost:8000/api/docs
# Database at: localhost:5432
```

### Option 2: Manual Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your settings

# Start PostgreSQL (if not using Docker)
# Then run database setup
python scripts/setup_neon.py

# Start the API
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Deployment Guide (Free Tier)

This project is configured for deployment on free tiers:
- **Frontend**: Vercel (Hobby plan)
- **Backend**: Render.com (Free tier)
- **Database**: Neon (Free tier)

### Step 1: Set Up Neon PostgreSQL

1. Create an account at [neon.tech](https://neon.tech)
2. Create a new project (e.g., "eso-build-optimizer")
3. Copy your connection string from the dashboard
4. Note: Free tier includes:
   - 0.5 GB storage
   - 1 compute branch
   - Unlimited projects

```bash
# Test your connection locally
export DATABASE_URL="postgresql+asyncpg://user:pass@ep-xxx.region.aws.neon.tech/eso_optimizer?sslmode=require"
python scripts/setup_neon.py --dry-run
python scripts/setup_neon.py  # Run for real
```

### Step 2: Deploy Backend to Render

1. Create an account at [render.com](https://render.com)
2. Connect your GitHub repository
3. Create a new "Blueprint" deployment:
   - Select your repo
   - Render will auto-detect `render.yaml`
4. Or create a "Web Service" manually:
   - Environment: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
   - Set environment variables in dashboard:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | Your Neon connection string |
| `JWT_SECRET_KEY` | Auto-generate in Render |
| `ALLOWED_ORIGINS` | Your Vercel frontend URL |
| `ENVIRONMENT` | production |
| `DEBUG` | false |

**Free tier notes:**
- 750 hours/month (enough for one service)
- Spins down after 15 minutes of inactivity
- First request after sleep takes ~30 seconds

### Step 3: Deploy Frontend to Vercel

1. Create an account at [vercel.com](https://vercel.com)
2. Import your GitHub repository
3. Configure:
   - Framework Preset: Vite
   - Root Directory: `web`
   - Build Command: `npm run build`
   - Output Directory: `dist`
4. Set environment variables:

| Variable | Value |
|----------|-------|
| `VITE_API_URL` | Your Render backend URL |
| `VITE_APP_NAME` | ESO Build Optimizer |

5. Deploy!

**Hobby plan notes:**
- Unlimited deployments
- Automatic HTTPS
- Preview deployments for PRs

### Step 4: Configure CORS

After deployment, update your Render environment:

```
ALLOWED_ORIGINS=https://your-app.vercel.app,https://your-custom-domain.com
```

### Step 5: Verify Deployment

```bash
# Check API health
curl https://your-app.onrender.com/health

# Check API docs
open https://your-app.onrender.com/api/docs
```

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `JWT_SECRET_KEY` | Yes | - | Secret for JWT tokens |
| `ALLOWED_ORIGINS` | Yes | localhost | CORS allowed origins |
| `ENVIRONMENT` | No | development | development/staging/production |
| `DEBUG` | No | false | Enable debug mode |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | No | 60 | Rate limit per user |
| `RATE_LIMIT_REQUESTS_PER_DAY` | No | 10000 | Daily rate limit |

See `.env.example` for full list.

---

## API Documentation

Once deployed, access the interactive API docs:
- Swagger UI: `/api/docs`
- ReDoc: `/api/redoc`
- OpenAPI JSON: `/api/openapi.json`

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/v1/auth/register` | POST | User registration |
| `/api/v1/auth/login` | POST | User login |
| `/api/v1/runs` | GET/POST | Combat runs |
| `/api/v1/features` | GET | Feature database |
| `/api/v1/recommendations/{run_id}` | GET | Get recommendations |

---

## Database Setup

### Create Tables

```bash
# Using the setup script
export DATABASE_URL="your-connection-string"
python scripts/setup_neon.py
```

### Seed Data

The setup script automatically seeds:
- Features from `data/raw/phase*.json`
- Gear Sets from `data/raw/sets_*.json`

```bash
# Seed only (tables already exist)
python scripts/setup_neon.py --seed-only

# Drop and recreate everything
python scripts/setup_neon.py --drop-all

# Preview changes
python scripts/setup_neon.py --dry-run
```

---

## Docker Commands

```bash
# Start all services
docker-compose -f docker/docker-compose.dev.yml up

# Start with pgAdmin (database UI)
docker-compose -f docker/docker-compose.dev.yml --profile tools up

# Rebuild after code changes
docker-compose -f docker/docker-compose.dev.yml up --build

# Stop all services
docker-compose -f docker/docker-compose.dev.yml down

# Stop and remove volumes (WARNING: deletes data)
docker-compose -f docker/docker-compose.dev.yml down -v
```

---

## Data Management

### Generate Excel from JSON

```bash
python scripts/generate_excel.py
```

### Count Features

```bash
for f in data/raw/*.json; do
  echo "$f: $(python3 -c "import json; print(len(json.load(open('$f'))))")"
done
```

### Validate JSON

```bash
python -m json.tool data/raw/phase01_class_skills.json > /dev/null && echo "Valid"
```

---

## Monitoring & Troubleshooting

### Check Render Logs

```bash
# Via Render dashboard or CLI
render logs --service eso-build-optimizer-api
```

### Common Issues

1. **Database connection fails**
   - Check Neon is not sleeping (free tier)
   - Verify `?sslmode=require` in connection string
   - Check IP allowlist if configured

2. **Render service sleeps**
   - Free tier spins down after 15min inactivity
   - Consider external ping service (e.g., UptimeRobot)

3. **CORS errors**
   - Verify `ALLOWED_ORIGINS` includes your frontend URL
   - Include both www and non-www versions

4. **JWT authentication fails**
   - Ensure `JWT_SECRET_KEY` is consistent across restarts
   - Check token expiration settings

---

## Cost Breakdown (Free Tier)

| Service | Tier | Limitations |
|---------|------|-------------|
| Neon | Free | 0.5GB storage, auto-suspend |
| Render | Free | 750hrs/month, 15min sleep |
| Vercel | Hobby | 100GB bandwidth, 100 deployments |

**Estimated monthly cost: $0**

For production, consider:
- Neon Pro ($19/mo) - 10GB, no suspend
- Render Starter ($7/mo) - no sleep, custom domains
- Vercel Pro ($20/mo) - team features, analytics

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## License

Data compiled from publicly available ESO game information for educational and optimization purposes.
