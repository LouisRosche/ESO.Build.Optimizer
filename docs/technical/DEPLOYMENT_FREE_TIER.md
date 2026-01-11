# Free Tier Deployment Guide

> **Last Updated**: January 2026
> **Stack**: Vercel (Frontend) + Render (Backend) + Neon (PostgreSQL)
> **Sources**: [Neon Pricing](https://neon.com/pricing), [Render Free Tier](https://render.com/docs/free), [Vercel Pricing](https://vercel.com/pricing)

---

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     Vercel      │────▶│     Render      │────▶│      Neon       │
│   (Frontend)    │     │   (FastAPI)     │     │  (PostgreSQL)   │
│   React SPA     │     │   Python API    │     │   Serverless    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
     FREE tier              FREE tier              FREE tier
```

---

## Neon PostgreSQL Free Tier

### Limits (as of August 2025)

| Resource | Free Tier Limit |
|----------|-----------------|
| **Compute** | 100 CU-hours/month |
| **Storage** | 0.5 GB per project |
| **Projects** | Up to 20 projects |
| **Data Transfer** | 5 GB egress/month |
| **Branches** | Unlimited (but storage shared) |

### Key Behaviors

1. **Auto-suspend**: Databases suspend after 5 minutes of inactivity (saves compute hours)
2. **Cold start**: First query after suspend takes ~500ms-2s
3. **No expiration**: Free tier doesn't expire (unlike Render Postgres)

### Optimization Tips

```python
# Use connection pooling to minimize cold starts
DATABASE_URL = "postgresql://user:pass@ep-xyz.us-east-2.aws.neon.tech/db?sslmode=require"

# Neon connection string format includes pooler by default
# For direct connection (migrations): use ?options=endpoint%3Dep-xyz
```

### Cost Calculation

```
0.25 CU running continuously = 0.25 × 24 × 30 = 180 CU-hours (over limit)
0.25 CU with auto-suspend (8hr active/day) = 0.25 × 8 × 30 = 60 CU-hours (safe)
```

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
2. **Cold start**: 30-60 seconds to wake up
3. **No persistent disk**: Filesystem resets on restart/sleep
4. **Free Postgres expires**: 30 days only (use Neon instead!)

### Keep-Alive Strategy

```python
# In your FastAPI app
import asyncio
from aiocron import crontab

@crontab("*/10 * * * *")  # Every 10 minutes
async def keep_alive():
    """Prevent Render sleep by self-pinging."""
    import httpx
    async with httpx.AsyncClient() as client:
        await client.get("https://your-app.onrender.com/health")
```

**Alternative**: Use [UptimeRobot](https://uptimerobot.com/) (free) to ping `/health` every 5 minutes.

### render.yaml Configuration

```yaml
services:
  - type: web
    name: eso-build-optimizer-api
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
    envVars:
      - key: DATABASE_URL
        sync: false  # Set manually in dashboard
      - key: ENVIRONMENT
        value: production
```

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

### Best Practices

1. **Static export when possible**: Reduces serverless usage
2. **Use ISR (Incremental Static Regeneration)** for semi-dynamic pages
3. **API routes timeout at 10s**: Heavy compute must go to Render

### vercel.json Configuration

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://your-api.onrender.com/:path*"
    }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" }
      ]
    }
  ]
}
```

---

## Environment Variables

### Never Commit Secrets

```bash
# .env.example (commit this)
DATABASE_URL=postgresql://user:pass@host/db
JWT_SECRET=your-secret-here
API_URL=http://localhost:8000

# .env (never commit)
DATABASE_URL=postgresql://actual:credentials@neon.tech/db
JWT_SECRET=super-secret-production-key
API_URL=https://your-api.onrender.com
```

### Syncing Across Platforms

```bash
# Vercel: Set in dashboard or CLI
vercel env add DATABASE_URL production

# Render: Set in dashboard (Environment tab)

# Local development
cp .env.example .env
# Edit .env with local values
```

---

## Monitoring Free Tier Usage

### Neon
- Dashboard → Project → Usage tab
- Set alerts at 80% compute usage

### Render
- Dashboard → Service → Metrics
- Monitor sleep/wake cycles

### Vercel
- Dashboard → Project → Analytics
- Watch bandwidth and function invocations

---

## Scaling Beyond Free Tier

When you outgrow free tier:

| Platform | Next Tier | Cost | Key Upgrade |
|----------|-----------|------|-------------|
| Neon | Launch | $19/mo | 300 CU-hours, 10 GB storage |
| Render | Starter | $7/mo | No sleep, 512 MB RAM |
| Vercel | Pro | $20/mo | 1 TB bandwidth, 1000 GB-hours |

**Recommendation**: Start with Render upgrade first - eliminates cold starts which impact UX most.

---

## Deployment Checklist

- [ ] Set all environment variables in each platform
- [ ] Configure health check endpoint
- [ ] Set up keep-alive for Render (if needed)
- [ ] Enable Neon auto-suspend
- [ ] Configure CORS for cross-origin API calls
- [ ] Test cold start times
- [ ] Set up monitoring/alerts
- [ ] Configure custom domain (optional)

---

*This document should be refreshed when platforms update their free tier limits.*
