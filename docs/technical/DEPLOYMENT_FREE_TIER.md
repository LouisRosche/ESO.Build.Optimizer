# Free Tier Deployment Guide

> **Last Updated**: January 2026
> **Stack**: Vercel (Frontend) + Render (Backend) + Neon (PostgreSQL)
> **Sources**: [Neon Pricing](https://neon.com/pricing), [Render Free Tier](https://render.com/docs/free), [Vercel Pricing](https://vercel.com/pricing)

---

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     Vercel      │────>│     Render      │────>│      Neon       │
│   (Frontend)    │     │   (FastAPI)     │     │  (PostgreSQL)   │
│   React SPA     │     │   Python API    │     │   Serverless    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
     FREE tier              FREE tier              FREE tier
```

### Data Flow

1. **User** visits Vercel-hosted React app
2. **Frontend** makes API calls to Render backend (via CORS)
3. **Backend** queries Neon PostgreSQL for data
4. **ML Pipeline** runs on Render for percentile calculations
5. **Recommendations** generated and returned to user

---

## Neon PostgreSQL Free Tier

### Limits (as of January 2026)

| Resource | Free Tier Limit |
|----------|-----------------|
| **Compute** | 100 CU-hours/month |
| **Storage** | 0.5 GB per project |
| **Projects** | Up to 20 projects |
| **Data Transfer** | 5 GB egress/month |
| **Branches** | Unlimited (storage shared) |

### Key Behaviors

1. **Auto-suspend**: Databases suspend after 5 minutes of inactivity (saves compute hours)
2. **Cold start**: First query after suspend takes ~500ms-2s
3. **No expiration**: Free tier does not expire (unlike Render Postgres which has 90-day limit)
4. **Connection pooling**: Built into Neon connection strings

### Connection String Format

```python
# Standard connection (with pooler - recommended)
DATABASE_URL = "postgresql+asyncpg://user:pass@ep-xyz.us-east-2.aws.neon.tech/db?sslmode=require"

# Direct connection (for migrations, bypasses pooler)
# Add ?options=endpoint%3Dep-xyz to use direct connection
DIRECT_URL = "postgresql://user:pass@ep-xyz.us-east-2.aws.neon.tech/db?sslmode=require&options=endpoint%3Dep-xyz"
```

### Compute Hour Calculation

```
# Continuous usage (over limit)
0.25 CU running 24/7 = 0.25 x 24 x 30 = 180 CU-hours/month (EXCEEDS FREE TIER)

# With auto-suspend (8hr active/day) - typical for dev/small apps
0.25 CU x 8 hrs x 30 days = 60 CU-hours/month (within limit)

# Light usage (4hr active/day) - typical for side projects
0.25 CU x 4 hrs x 30 days = 30 CU-hours/month (plenty of headroom)
```

### Optimization Tips

- **Enable auto-suspend**: On by default, do not disable
- **Use connection pooling**: Reduces connection overhead on wake-up
- **Batch database operations**: Minimize round-trips
- **Cache frequently accessed data**: Use Redis or in-memory caching

---

## Render Free Tier

### Limits

| Resource | Free Tier Limit |
|----------|-----------------|
| **Instance Hours** | 750 hours/month (per service) |
| **RAM** | 512 MB |
| **CPU** | 0.1 CPU |
| **Bandwidth** | 100 GB/month |
| **Sleep Timeout** | 15 minutes inactivity |

### Critical Behaviors

1. **Sleep after 15 min**: Service spins down without traffic
2. **Cold start**: 30-60 seconds to wake up (Python apps)
3. **No persistent disk**: Filesystem resets on restart/sleep
4. **Free Postgres expires**: 90 days only - use Neon instead

### render.yaml Configuration

The project includes a `render.yaml` blueprint:

```yaml
services:
  - type: web
    name: eso-build-optimizer-api
    runtime: python
    region: oregon  # or: ohio, frankfurt, singapore
    plan: free
    branch: main

    # Build configuration
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn api.main:app --host 0.0.0.0 --port $PORT

    # Health check (critical for Render monitoring)
    healthCheckPath: /health

    # Environment variables
    envVars:
      - key: ENVIRONMENT
        value: production
      - key: DEBUG
        value: false
      - key: DATABASE_URL
        sync: false  # Set manually in Render dashboard
      - key: JWT_SECRET_KEY
        generateValue: true  # Render generates secure random value
      - key: ALLOWED_ORIGINS
        sync: false  # Set to your Vercel frontend URL
      - key: PYTHON_VERSION
        value: 3.11.0
      - key: RATE_LIMIT_REQUESTS_PER_MINUTE
        value: 60
      - key: RATE_LIMIT_REQUESTS_PER_DAY
        value: 10000

    autoDeploy: true
```

### Keep-Alive Strategies

The Render free tier spins down after 15 minutes of inactivity. Here are strategies to keep the service warm:

#### Option 1: External Monitoring Service (Recommended)

Use [UptimeRobot](https://uptimerobot.com/) (free tier: 50 monitors):

1. Create account at uptimerobot.com
2. Add HTTP(s) monitor for `https://your-app.onrender.com/health`
3. Set interval to **5 minutes** (free tier minimum)
4. Enable alerts for downtime

Other free alternatives:
- [Freshping](https://www.freshworks.com/website-monitoring/) - 50 monitors
- [Cron-job.org](https://cron-job.org/) - Free cron jobs

#### Option 2: Self-Ping in Application

Add a background task to the FastAPI application:

```python
# api/core/keep_alive.py
import asyncio
import logging
from contextlib import asynccontextmanager

import httpx

logger = logging.getLogger(__name__)

KEEP_ALIVE_INTERVAL = 600  # 10 minutes (must be < 15 min)
SELF_URL = "https://your-app.onrender.com/health"

async def keep_alive_task():
    """Background task to prevent Render sleep."""
    async with httpx.AsyncClient() as client:
        while True:
            await asyncio.sleep(KEEP_ALIVE_INTERVAL)
            try:
                response = await client.get(SELF_URL, timeout=30)
                logger.debug(f"Keep-alive ping: {response.status_code}")
            except Exception as e:
                logger.warning(f"Keep-alive failed: {e}")

@asynccontextmanager
async def lifespan_with_keepalive(app):
    """Lifespan with keep-alive task."""
    # Start keep-alive task
    task = asyncio.create_task(keep_alive_task())

    yield

    # Cancel on shutdown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
```

**Note**: Self-ping uses your instance hours. With 750 hrs/month limit, running 24/7 (720 hrs) leaves minimal headroom.

#### Option 3: GitHub Actions Scheduled Ping

Add to `.github/workflows/keep-alive.yml`:

```yaml
name: Keep Render Alive

on:
  schedule:
    - cron: '*/10 * * * *'  # Every 10 minutes

jobs:
  ping:
    runs-on: ubuntu-latest
    steps:
      - name: Ping Render service
        run: curl -f https://your-app.onrender.com/health || exit 0
```

**Warning**: GitHub Actions has minute limits on free tier. Use sparingly.

---

## Vercel Free Tier

### Limits

| Resource | Free Tier Limit |
|----------|-----------------|
| **Deployments** | Unlimited |
| **Bandwidth** | 100 GB/month |
| **Serverless Execution** | 100 GB-hours/month |
| **Function Duration** | 10 seconds max |
| **Builds** | 6000 minutes/month |
| **Team Members** | 1 (Hobby plan) |

### Best Practices

1. **Static export when possible**: Reduces serverless usage
2. **Use ISR** for semi-dynamic pages
3. **API routes timeout at 10s**: Heavy compute must go to Render
4. **Leverage edge caching**: Use `Cache-Control` headers

### vercel.json Configuration

The project includes `web/vercel.json`:

```json
{
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ],
  "headers": [
    {
      "source": "/assets/(.*)",
      "headers": [
        {
          "key": "Cache-Control",
          "value": "public, max-age=31536000, immutable"
        }
      ]
    }
  ]
}
```

### API Proxy Configuration

For production, add API proxy rewrites to avoid CORS:

```json
{
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://your-api.onrender.com/api/:path*"
    },
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

---

## Environment Variables

### Backend (.env.example)

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `DATABASE_URL` | Yes | Neon PostgreSQL connection string | `postgresql+asyncpg://user:pass@host/db?sslmode=require` |
| `JWT_SECRET_KEY` | Yes | Secret for JWT tokens (generate secure value) | `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `ENVIRONMENT` | Yes | Runtime environment | `development`, `staging`, `production` |
| `DEBUG` | No | Enable debug mode | `true`, `false` (default: `false`) |
| `ALLOWED_ORIGINS` | Yes | CORS allowed origins (comma-separated) | `https://your-app.vercel.app,https://custom-domain.com` |
| `API_V1_PREFIX` | No | API route prefix | `/api/v1` (default) |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | No | Rate limit per user/minute | `60` (default) |
| `RATE_LIMIT_REQUESTS_PER_DAY` | No | Rate limit per user/day | `10000` (default) |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | No | Access token TTL | `30` (default) |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | No | Refresh token TTL | `7` (default) |
| `REDIS_URL` | No | Redis for caching (optional) | `redis://localhost:6379/0` |
| `SENTRY_DSN` | No | Sentry error tracking (optional) | `https://xxx@sentry.io/xxx` |
| `CURRENT_PATCH` | No | ESO game patch version | `U48` |

### Frontend (.env)

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `VITE_API_URL` | Yes | Backend API base URL | `https://your-api.onrender.com/api/v1` |

### Platform-Specific Variables (Auto-set)

These are automatically set by hosting platforms:

| Variable | Platform | Description |
|----------|----------|-------------|
| `PORT` | Render | Port to bind server |
| `RENDER_EXTERNAL_URL` | Render | Public URL of service |
| `VERCEL_URL` | Vercel | Deployment URL |
| `VERCEL_ENV` | Vercel | Environment (production/preview/development) |

### Setting Environment Variables

```bash
# Vercel CLI
vercel env add DATABASE_URL production
vercel env add JWT_SECRET_KEY production --sensitive

# Render: Use dashboard (Environment tab) or render.yaml
# Neon: Connection string from Neon dashboard

# Local development
cp .env.example .env
# Edit .env with local values
```

### Security: Never Commit Secrets

```gitignore
# .gitignore (already configured)
.env
.env.local
.env.production
*.pem
```

---

## CI/CD Pipeline Integration

The project includes a comprehensive CI pipeline at `.github/workflows/ci.yml`.

### Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     GitHub Actions CI                           │
├─────────────────┬─────────────────┬─────────────────────────────┤
│  python-tests   │  frontend-tests │  lua-validation             │
│  - Syntax check │  - TypeScript   │  - Lua syntax               │
│  - Unit tests   │  - ESLint       │  - Luacheck lint            │
│  - Import check │  - Build test   │                             │
├─────────────────┴─────────────────┴─────────────────────────────┤
│  data-validation          │  security-scan                      │
│  - JSON validation        │  - Bandit security scan             │
│  - Feature count check    │                                     │
├───────────────────────────┴─────────────────────────────────────┤
│                          build                                   │
│  - Build frontend          (depends on all above jobs)          │
│  - Generate Excel data                                          │
│  - Upload artifacts                                             │
└─────────────────────────────────────────────────────────────────┘
```

### Trigger Conditions

```yaml
on:
  push:
    branches: [main, 'claude/**']
  pull_request:
    branches: [main]
```

### Jobs Summary

| Job | Description | Tools |
|-----|-------------|-------|
| `python-tests` | Python syntax, imports, and unit tests | Python 3.11, pytest |
| `frontend-tests` | TypeScript, ESLint, build verification | Node 20, npm |
| `lua-validation` | Addon Lua syntax and linting | Lua 5.1, luacheck |
| `data-validation` | JSON schema and feature count validation | Python json module |
| `security-scan` | Static security analysis | Bandit |
| `build` | Build artifacts (frontend, Excel) | npm, Python |

### Artifacts Generated

- `frontend-dist`: Production build of React app
- `excel-data`: Generated Excel files from JSON data

### Deployment Integration

**Vercel** (auto-deploy):
1. Connect GitHub repo in Vercel dashboard
2. Set root directory to `web/`
3. Vercel auto-deploys on push to `main`

**Render** (auto-deploy):
1. Connect GitHub repo in Render dashboard
2. Set `autoDeploy: true` in render.yaml
3. Render auto-deploys on push to `main`

### Manual Deployment

```bash
# Vercel (frontend)
cd web
vercel --prod

# Render (backend)
# Use Render dashboard or Git push to trigger deploy
```

---

## Monitoring Free Tier Usage

### Neon Dashboard

1. Go to [Neon Console](https://console.neon.tech/)
2. Select project > **Usage** tab
3. Monitor:
   - Compute hours used/remaining
   - Storage used
   - Data transfer

**Set alerts**: Configure email notifications at 80% usage threshold.

### Render Dashboard

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Select service > **Metrics** tab
3. Monitor:
   - Memory usage (512 MB limit)
   - CPU usage
   - Request latency
   - Sleep/wake cycles

### Vercel Dashboard

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Select project > **Analytics** tab
3. Monitor:
   - Bandwidth usage
   - Function invocations
   - Build minutes

---

## Troubleshooting

### Neon Issues

| Problem | Solution |
|---------|----------|
| "Connection timeout" | Database is waking from suspend. Retry after 2s. |
| "Too many connections" | Use connection pooling in DATABASE_URL |
| "Compute hours exceeded" | Check for runaway queries, optimize access patterns |
| "SSL required" | Ensure `?sslmode=require` in connection string |

### Render Issues

| Problem | Solution |
|---------|----------|
| 30-60s response time | First request after sleep. Implement keep-alive. |
| "Memory limit exceeded" | Optimize memory usage, check for leaks |
| "Build failed" | Check requirements.txt, Python version |
| Health check failing | Ensure `/health` endpoint returns 200 |

### Vercel Issues

| Problem | Solution |
|---------|----------|
| CORS errors | Configure ALLOWED_ORIGINS on backend |
| API timeout (10s) | Move heavy operations to Render backend |
| Build failing | Check Node version, dependencies |
| 404 on routes | Ensure SPA rewrite in vercel.json |

### Cold Start Mitigation

```python
# In FastAPI, warm up connections on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm up database connection
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
        logger.info("Database connection warmed up")

    yield
```

---

## Scaling Beyond Free Tier

When you outgrow free tier:

| Platform | Next Tier | Monthly Cost | Key Upgrade |
|----------|-----------|--------------|-------------|
| Neon | Launch | $19/mo | 300 CU-hours, 10 GB storage |
| Render | Starter | $7/mo | No sleep, 512 MB RAM |
| Vercel | Pro | $20/mo | 1 TB bandwidth, 1000 GB-hours |

### Upgrade Priority

1. **Render first** - Eliminates cold starts (30-60s delays hurt UX most)
2. **Neon second** - More compute hours for growth
3. **Vercel last** - 100 GB bandwidth is usually sufficient

### Cost-Effective Scaling Path

```
Free Tier ($0/mo)
    │
    ▼ (500+ daily active users)
Render Starter ($7/mo)
    │
    ▼ (Complex queries, more data)
Neon Launch ($19/mo)
    │
    ▼ (High traffic, team features)
Vercel Pro ($20/mo)
    │
    Total: $46/mo for a robust production setup
```

---

## Deployment Checklist

### Initial Setup

- [ ] Create accounts on Vercel, Render, Neon (all free)
- [ ] Create Neon database, copy connection string
- [ ] Generate secure JWT secret: `python -c "import secrets; print(secrets.token_urlsafe(64))"`
- [ ] Configure Render environment variables
- [ ] Configure Vercel environment variables
- [ ] Connect GitHub repositories for auto-deploy

### Pre-Launch

- [ ] Set `ENVIRONMENT=production` on Render
- [ ] Set `DEBUG=false` on Render
- [ ] Configure `ALLOWED_ORIGINS` with Vercel URL
- [ ] Test health check endpoint: `curl https://your-api.onrender.com/health`
- [ ] Test database connectivity via health check response
- [ ] Set up keep-alive for Render (UptimeRobot recommended)

### Security

- [ ] Verify JWT secret is not default value
- [ ] Enable Neon SSL (`?sslmode=require`)
- [ ] Review CORS configuration
- [ ] Set up rate limiting (configured by default)

### Monitoring

- [ ] Set Neon usage alerts at 80%
- [ ] Configure UptimeRobot notifications
- [ ] Enable Vercel Analytics (free tier available)

### Post-Launch

- [ ] Monitor cold start times
- [ ] Check for memory leaks (Render metrics)
- [ ] Validate rate limiting is working
- [ ] Test authentication flow end-to-end

---

## Quick Reference

### URLs After Deployment

```
Frontend: https://eso-build-optimizer.vercel.app
Backend:  https://eso-build-optimizer-api.onrender.com
API Docs: https://eso-build-optimizer-api.onrender.com/api/docs
Health:   https://eso-build-optimizer-api.onrender.com/health
```

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check (Render uses this) |
| `/api/v1/auth/register` | POST | User registration |
| `/api/v1/auth/login` | POST | User login |
| `/api/v1/runs` | GET/POST | Combat runs |
| `/api/v1/recommendations` | GET | Build recommendations |
| `/api/docs` | GET | Swagger UI |

### Useful Commands

```bash
# Check API health
curl https://your-api.onrender.com/health

# Test database connection (via health endpoint)
curl https://your-api.onrender.com/health | jq '.database'

# Deploy frontend manually
cd web && vercel --prod

# View Render logs
# (Use Render dashboard > Logs tab)

# Validate CI locally
act -j python-tests  # requires act CLI
```

---

*This document should be refreshed when platforms update their free tier limits or when major infrastructure changes occur.*
