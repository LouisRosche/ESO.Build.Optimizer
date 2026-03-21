# ESO Build Optimizer - AI Agent Instructions

An ESO combat analytics system: Lua addon tracks metrics in-game, companion app syncs to cloud, ML pipeline generates percentile comparisons and build recommendations via a web dashboard.

---

## Architecture Overview

```
ESO Client (Lua Addon) --> SavedVariables/*.lua --> Companion App (Python)
    --> HTTPS --> FastAPI Backend --> PostgreSQL (Neon)
                                 --> ML Pipeline (percentile + recs)
                                 --> React Frontend (Vercel)
```

| Component | Stack | Location |
|-----------|-------|----------|
| Lua Addons | Lua 5.1, ESO API | `addon/ESOBuildOptimizer/`, `addon/FurnishProfitTargeter/` |
| Companion App | Python | `companion/` |
| Web API | FastAPI | `api/` |
| ML Pipeline | Python, scikit-learn | `ml/` |
| Web Frontend | React/Vite/TypeScript | `web/` |
| Addon Fixer | TypeScript CLI | `tools/addon-fixer/` |
| Feature Data | JSON | `data/raw/` (37 files, ~1,981 entries; `phase*` = skills, `sets_*` = gear) |

---

## File Structure

```
ESO.Build.Optimizer/
├── addon/
│   ├── ESOBuildOptimizer/        # Combat analytics addon
│   │   ├── ESOBuildOptimizer.txt/.addon/.lua
│   │   └── modules/             # CombatTracker, BuildSnapshot, MetricsUI, SkillAdvisor
│   └── FurnishProfitTargeter/    # Furnishing profit optimizer
│       ├── FurnishProfitTargeter.txt/.addon/.lua
│       ├── modules/              # 7 modules
│       └── ui/                   # ResultsWindow.xml
├── api/                          # FastAPI backend
│   ├── main.py, core/, models/, routes/
│   └── alembic/                  # DB migrations
├── companion/                    # Desktop sync app
│   ├── watcher.py, sync.py, cmx_parser.py
│   └── build.py/.spec            # PyInstaller packaging
├── ml/
│   ├── percentile.py             # Percentile calculation
│   └── recommendations.py       # Recommendation engine
├── web/src/                      # React frontend
│   ├── pages/                    # Dashboard, Builds, Analytics, etc.
│   ├── components/               # UI components
│   └── data/mockData.ts          # Placeholder data (no real API integration yet)
├── data/
│   ├── raw/                      # Feature JSON files (skills, sets, CP, companions)
│   ├── compiled/                 # Generated Excel
│   ├── schemas/                  # JSON Schema definitions
│   └── migrations/               # ESO API migration database
├── tools/addon-fixer/            # TypeScript CLI for fixing broken ESO addons
├── scripts/                      # Utility scripts (generate_excel, validate_*, etc.)
├── tests/                        # pytest suite
└── docs/                         # Domain knowledge, schemas, technical guides
```

---

## Task Routing

| Task Type | Where to Work | Key Files |
|-----------|---------------|-----------|
| Lua addon code | `addon/*/` | Follow ESO API patterns in `docs/technical/ESO_ADDON_API.md` |
| Feature data | `data/raw/` | Run `python scripts/generate_excel.py` after changes |
| Backend API | `api/` | See `docs/technical/FASTAPI_BEST_PRACTICES.md` |
| ML pipeline | `ml/` | `percentile.py`, `recommendations.py` |
| Web frontend | `web/` | See `docs/technical/REACT_VITE_BEST_PRACTICES.md` |
| Addon fixer | `tools/addon-fixer/` | TypeScript, run `npm test` after changes |
| Deployment | `docker/`, `render.yaml`, `web/vercel.json` | See `docs/technical/DEPLOYMENT_FREE_TIER.md` |

---

## Coding Standards

**Lua (Addon):**
- Use local variables, namespace all events
- Register with `EVENT_MANAGER:RegisterForEvent(ADDON_NAME, ...)`
- Filter events to reduce callback frequency
- Data persists on zone change/logout only

**Python (Backend/ML):**
- Type hints required
- Use Pydantic for schemas, dataclasses for internal models
- `async def` for I/O operations

**JSON Data:**
- snake_case keys, `null` for missing optional fields

**TypeScript (Addon Fixer / Web):**
- Strict mode, prefer `const` over `let`

---

## Current State (Honest Assessment)

### Done:
- [x] Feature dataset (1,981 entries across 37 JSON files)
- [x] Excel generation pipeline
- [x] Lua addons (ESOBuildOptimizer + FurnishProfitTargeter) with ESO best practices
- [x] TypeScript addon fixer CLI with migration database
- [x] CI/CD pipeline (GitHub Actions, 7 jobs)
- [x] Technical documentation system (5 guides in `docs/technical/`)

### Scaffolding (structure exists, not production-ready):
- [ ] Web frontend — renders mock data only, no real API integration
- [ ] FastAPI backend — endpoints defined, no production database connected
- [ ] ML pipeline — algorithms implemented, untested against real combat data
- [ ] Companion app — file watcher + sync logic written, not packaged or tested end-to-end

### Not Started:
- [ ] ESOUI.com addon submission
- [ ] Production deployment
- [ ] Companion app installer packaging
- [ ] Web scraping scripts (data sources identified but no scrapers exist)

---

## Quick Reference

```bash
# Run all Python tests
pytest tests/ -v

# Validate JSON data
python scripts/validate_data.py

# Generate Excel from JSON
python scripts/generate_excel.py

# Addon fixer CLI
cd tools/addon-fixer
node dist/cli.js analyze /path/to/addon
node dist/cli.js fix /path/to/addon
node dist/cli.js verify /path/to/addon
node dist/cli.js migrations
node dist/cli.js info

# FurnishProfitTargeter validation
python scripts/test_fpt_prepublish.py
python scripts/validate_fpt_addon.py

# Makefile shortcuts
make test          # All tests
make fixer-build   # Build addon fixer
make fpt-test      # FPT test suite
```

---

## Key Domain References

- **ESO game systems**: `docs/ESO_DOMAIN_KNOWLEDGE.md` (classes, gear, combat metrics, API constraints)
- **Data schemas**: `docs/DATA_SCHEMAS.md` (feature, combat run, recommendation, gear set)
- **ESO Addon API**: `docs/technical/ESO_ADDON_API.md`
- **Addon fixer details**: `tools/addon-fixer/README.md`

## Lessons Learned

**Lua Parser (luaparse):** `StringLiteral.value` is often null — use `node.value ?? node.raw?.slice(1, -1)`.

**Pattern matching:** `"WINDOW_MANAGER:CreateControl"` matches `CreateControlFromVirtual` too — include the opening paren for exact match.

**Data sources:** UESP, ESO-Hub, ESO-Log, ESO-Sets. Exclude Alcast (opinion-based).

## Project Decisions

| Decision | Resolution |
|----------|------------|
| Privacy | Anonymous by default, opt-in for richer sharing |
| Content scope | PvE only (dungeons, trials, arenas). No PvP |
| Hosting | Free tier: Vercel + Render + Neon |
| Companion platforms | Windows primary; Mac/Linux via cross-platform Python |
| In-game UI | Minimal default with opt-in expander |

---

*Last updated: March 2026 | ESO Update 49 (API 101049)*
