# Production Deployment Runbook

Step-by-step instructions for deploying the ESO Build Optimizer to production.

---

## Prerequisites

- Neon account (free tier): https://neon.tech
- Render account (free tier): https://render.com
- Vercel account (free tier): https://vercel.com
- ESOUI.com account: https://www.esoui.com
- Git repo pushed to GitHub

---

## 1. Database (Neon PostgreSQL)

### Create Database
1. Sign up at https://neon.tech
2. Create a new project: "ESO Build Optimizer"
3. Copy the connection string (PostgreSQL format)
4. Convert to asyncpg format:
   ```
   # Neon gives you:
   postgresql://user:pass@ep-xxx.region.aws.neon.tech/dbname?sslmode=require

   # Change to asyncpg:
   postgresql+asyncpg://user:pass@ep-xxx.region.aws.neon.tech/dbname?sslmode=require
   ```

### Run Migrations
```bash
# Set the DATABASE_URL
export DATABASE_URL="postgresql+asyncpg://user:pass@ep-xxx.region.aws.neon.tech/dbname?sslmode=require"

# Apply all table schemas
cd api/
alembic upgrade head

# Verify tables created
# (Check Neon dashboard → SQL Editor → \dt)
```

### Seed Feature Data
```bash
# Load 1,981 features + gear sets from JSON
python scripts/seed_features.py --database-url "$DATABASE_URL"

# Verify counts
# Expected: 1,592 features + 389 gear sets
```

---

## 2. Backend (Render)

### Deploy via Blueprint
1. Go to https://dashboard.render.com
2. Click "New" → "Blueprint"
3. Connect your GitHub repo
4. Render auto-detects `render.yaml`

### Set Environment Variables in Render Dashboard
| Variable | Value |
|----------|-------|
| `DATABASE_URL` | Your Neon asyncpg connection string |
| `JWT_SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `ALLOWED_ORIGINS` | Your Vercel URL (e.g., `https://eso-build-optimizer.vercel.app`) |
| `ENVIRONMENT` | `production` |
| `DEBUG` | `false` |

### Verify
```bash
# Health check (replace with your Render URL)
curl https://eso-build-optimizer-api.onrender.com/health
# Expected: {"status": "healthy", "version": "0.1.0", "database": "connected"}
```

**Note:** Free-tier Render services sleep after 15 minutes of inactivity. First request after sleep takes ~30 seconds.

---

## 3. Frontend (Vercel)

### Deploy
1. Go to https://vercel.com/new
2. Import your GitHub repo
3. Set **Root Directory** to `web`
4. Framework: Vite (auto-detected)
5. Add environment variable:
   - `VITE_API_URL` = `https://eso-build-optimizer-api.onrender.com/api/v1`

### Verify
- Open your Vercel URL
- Dashboard should load (mock data in dev, real data when API is up)
- Check browser console for API connection errors

---

## 4. ESOUI Addon Submission

### Build Packages
```bash
# Both packages are pre-built in dist/
make esbo-package    # Creates dist/ESOBuildOptimizer-v1.zip (24 KB)
make fpt-package     # Creates dist/FurnishProfitTargeter-v1.zip (38 KB)
```

### Submit to ESOUI.com
1. Go to https://www.esoui.com → Log in → "Upload AddOn"
2. **ESOBuildOptimizer**:
   - Title: ESO Build Optimizer
   - Category: Combat Mods
   - Version: 1.0.0
   - Game Version: 101049
   - Upload: `dist/ESOBuildOptimizer-v1.zip`
3. **FurnishProfitTargeter**:
   - Title: Furnish Profit Targeter
   - Category: Crafting
   - Version: 1.0.0
   - Game Version: 101049
   - Upload: `dist/FurnishProfitTargeter-v1.zip`

---

## 5. Companion App (Windows)

### Build Executable
```bash
cd companion

# Generate icons (if not already done)
python generate_icons.py

# Install build dependencies
pip install -r requirements.txt

# Build
python build.py
# Output: companion/dist/ESOBuildOptimizer.exe
```

### Test
1. Run `ESOBuildOptimizer.exe`
2. System tray icon should appear
3. Right-click → configure API URL and ESO path
4. Start ESO and play — watcher should detect SavedVariables changes

---

## Post-Deployment Checklist

- [ ] Neon database has all tables (`alembic current` shows head)
- [ ] Feature data seeded (1,592 features + 389 gear sets)
- [ ] Render health check returns `"database": "connected"`
- [ ] Vercel frontend loads and shows dashboard
- [ ] CORS works (frontend can call API without errors)
- [ ] Auth flow works (register → login → get token)
- [ ] Both addons visible on ESOUI.com
- [ ] Companion app connects to API

---

## Troubleshooting

### Render service won't start
- Check logs in Render dashboard
- Ensure `DATABASE_URL` uses `asyncpg` driver (not `psycopg2`)
- Ensure `JWT_SECRET_KEY` is at least 32 characters

### Frontend shows only mock data
- Check browser console for API errors
- Verify `VITE_API_URL` environment variable in Vercel
- Verify CORS: `ALLOWED_ORIGINS` in Render includes Vercel URL

### Alembic migration fails
- Ensure database is accessible from your machine
- Check SSL: Neon requires `?sslmode=require`
- Try: `cd api && alembic current` to verify connection

### Companion app can't find SavedVariables
- Default path: `~/Documents/Elder Scrolls Online/live/SavedVariables/`
- Use `--headless` flag for debugging: `python main.py --headless`
