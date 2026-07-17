# FindLeads - Algorithms Tracker

> Total: 75 algorithms | Completed: 75 | Remaining: 0

---

## ✅ Completed Algorithms (5)

- [x] **1. Email Validation** - `validator.py` - MX records, disposable filter, role-based, SMTP VRFY
- [x] **2. Hyper-Personalization** - `personalizer.py` - Website analysis (WhatsApp, SSL, phone, social, tech, pain points)
- [x] **3. Email Warm-up & Load Balancing** - `warmup.py` - Multi-account rotation, daily quotas, state persistence
- [x] **4. OSINT Targeting** - `osint.py` - Owner/decision maker finding via Google search + website scraping
- [x] **5. Trojan Horse Asset Generator** - `mockup.py` - Review response mockups, website mockups, stats mockups via Pillow

---

## 🔨 Deep OSINT Engine (8 algorithms)

- [x] **6. Tech Stack Detection** - `osint/tech_detector.py` - TechDetect/Wappalyzer - detect 7400+ technologies (CMS, frameworks, CDNs, analytics)
- [x] **7. WHOIS Lookup** - `osint/whois_lookup.py` - `python-whois` + `ipwhois` - domain registration info + owner + expiry date
- [x] **8. DNS Intelligence** - `osint/dns_intel.py` - `dnspython` - DNS records + reverse DNS analysis
- [x] **9. Sentiment Analysis** - `osint/sentiment.py` - `TextBlob`/`VADER` - review sentiment (negative/positive/neutral)
- [x] **10. Financial Health Analysis** - `osint/financial_health.py` - derive business financial health from sentiment + whois + reviews signals
- [x] **11. Hidden Emails Discovery** - `osint/hidden_emails.py` - `requests` + `BeautifulSoup` - find hidden emails in PDFs, CSS, JS files
- [x] **12. Domain History** - `osint/domain_history.py` - Wayback Machine API - website history + when design changed
- [x] **13. SSL Certificate Intelligence** - `osint/ssl_intel.py` - `ssl` module - certificate info + owner + expiry

---

## ✅ Knowledge Graph - DuckDB + NetworkX (7 algorithms)

> **Database Choice: DuckDB + NetworkX**
> - **DuckDB**: Storage + Analytics (embedded, no server, columnar, compressed, JSON support)
> - **NetworkX**: Graph queries in memory (BFS, shortest path, communities)
> - **Why**: DuckDB = fast analytics + compressed storage. NetworkX = graph algorithms. Neither alone is enough.

- [x] **14. Graph Database Setup** - `graph/database.py` - DuckDB + JSON columns - single file relational database
- [x] **15. Node Storage** - `graph/nodes.py` - store business, person, email, tech, review nodes
- [x] **16. Edge Storage** - `graph/edges.py` - store relationships (OWNS, USES_TECH, HAS_EMAIL, REVIEWED_BY)
- [x] **17. Graph Queries** - `graph/queries.py` - BFS, shortest path, community detection via NetworkX (in-memory from DuckDB)
- [x] **18. Data Sync** - `graph/sync.py` - sync data from CSV/PDF to Graph
- [x] **19. Incremental Updates** - `graph/incremental.py` - update data only when changed
- [x] **20. Export & Backup** - `graph/export.py` - export to JSON/CSV + upload to GitHub Artifacts

---

## ✅ Temporal Tracking & Change Detection (8 algorithms)

> **Why this matters**: Data without time dimension is a snapshot. Data WITH time dimension is intelligence.
> Monthly updates track business health over time - this is what makes data priceless.

- [x] **21. Snapshot System** - `temporal/snapshots.py` - take business state snapshots (rating, reviews, tech, health) on every scan
- [x] **22. Change Detection** - `temporal/changes.py` - compare current vs previous snapshot, detect rating drops, new reviews, no-reply periods
- [x] **23. Change Severity Scoring** - `temporal/severity.py` - classify changes as low/medium/high/critical
- [x] **24. Monthly Health Tracking** - `temporal/monthly.py` - track business health score over time (0-100)
- [x] **25. Alert Generation** - `temporal/alerts.py` - auto-generate alerts for critical changes (rating drop, domain expiring, no reply for 90 days)
- [x] **26. Trend Analysis** - `temporal/trends.py` - analyze trends across businesses/sectors (is beauty industry improving?)
- [x] **27. Decay Detection** - `temporal/decay.py` - detect businesses in decline (losing reviews, dropping rating, no activity)
- [x] **28. Opportunity Scoring** - `temporal/opportunity.py` - score businesses by opportunity level based on changes + health + timing

---

## ✅ Search & Filtering System (10 algorithms)

> **Why this matters**: Without search, data is a dump. With search, data is a weapon.
> User must be able to filter by: month, country, city, sector, health score, rating, activity level.

- [x] **29. Taxonomy System** - `search/taxonomy.py` - country/city/sector hierarchy (UAE > Dubai > beauty salons)
- [x] **30. Filter Engine** - `search/filters.py` - multi-criteria filtering (country + city + sector + month + health + rating)
- [x] **31. Query Builder** - `search/queries.py` - build DuckDB SQL queries from filter criteria
- [x] **32. Date Range Filters** - `search/date_filters.py` - filter by specific month, last month, last 3 months, custom range
- [x] **33. Geographic Filters** - `search/geo_filters.py` - filter by country, city, or all cities in a country
- [x] **34. Sector Filters** - `search/sector_filters.py` - filter by sector (beauty, medical, hospitality, retail, etc.)
- [x] **35. Health Filters** - `search/health_filters.py` - filter by health score (healthy, declining, critical, dead)
- [x] **36. Activity Filters** - `search/activity_filters.py` - filter by reply activity (active, slow, dormant, silent)
- [x] **37. Search CLI** - `search/cli.py` - command line interface for searches
- [x] **38. Search Reports** - `search/reports.py` - generate filtered PDF/CSV reports with statistics

---

## ✅ Automated Search & DB Storage Pipeline (7 algorithms)

> **The Brain**: Ties everything together — Scraper → Analyzer → Contact → Validator → OSINT → DB → Alerts → Reports

- [x] **Auto Scraper** - `pipeline/auto_scraper.py` - Automated Google Maps scraping with stealth (UA rotation + random delays)
- [x] **OSINT Runner** - `pipeline/osint_runner.py` - Deep OSINT scan on scraped businesses (tech, WHOIS, DNS, SSL, sentiment)
- [x] **DB Storage** - `pipeline/db_storage.py` - DuckDB storage (businesses + snapshots + scan_runs), upsert on duplicate
- [x] **Temporal Tracker** - `pipeline/temporal_tracker.py` - Snapshots after every run, change detection between snapshots
- [x] **Alert Engine** - `pipeline/alert_engine.py` - Critical alerts: low rating, review fatigue, low health, no website
- [x] **Report Generator** - `pipeline/report_generator.py` - CSV + TXT + JSON reports after each run
- [x] **Pipeline Orchestrator** - `pipeline/orchestrator.py` - Main 7-step pipeline: scrape → analyze → email → store → OSINT → alerts → reports

---

## ✅ Reinforcement Learning Outreach - RLO (5 algorithms)

- [x] **39. IMAP IDLE Listener** - `rlo/imap_listener.py` - `imap_tools` - receive replies instantly (free push notification)
- [x] **40. Response Classification** - `rlo/response_classifier.py` - `VADER Sentiment` - classify replies (positive/negative/spam)
- [x] **41. Prompt Scoring** - `rlo/prompt_scorer.py` - track which prompts worked and which failed
- [x] **42. Automated Feedback Loop** - `rlo/feedback_loop.py` - update prompt weights automatically via DuckDB
- [x] **43. Learning History** - `rlo/learning_history.py` - save all learning history to DuckDB

---

## ✅ Autonomous Agent (5 algorithms)

- [x] **44. LangGraph State Machine** - `agent/state_machine.py` - `LangGraph` - build AI "state machine" for smart agent
- [x] **45. Response Reading** - `agent/response_reader.py` - OpenRouter `llama-3.1-8b:free` - read and understand customer reply
- [x] **46. Auto-Reply Generation** - `agent/auto_reply.py` - OpenRouter `llama-3.1-8b:free` - generate appropriate auto-reply
- [x] **47. Meeting Scheduling** - `agent/scheduler.py` - `Cal.com` (open source) - book meetings automatically
- [x] **48. Conversation Memory** - `agent/memory.py` - DuckDB + Knowledge Graph - remember previous conversations

---

## ✅ Stealth & Distribution (12 algorithms)

> **Strategy**: All run in parallel for maximum coverage
> - GitHub Actions: scheduled runs (free IP rotation via Microsoft Azure)
> - Playwright Stealth: remove bot traces
> - Free Proxy Rotation: rotate IP per request
> - Random delays/UA/headers: human mimicry

- [x] **49. Playwright Stealth** - `stealth/playwright_stealth.py` - `playwright-stealth` - remove bot traces from browser
- [x] **50. Human Mouse Movement** - `stealth/human_mouse.py` - `pyautogui`/Playwright - natural random mouse movement
- [x] **51. Random Scrolling** - `stealth/scrolling.py` - Playwright - slow scrolling like a human reading
- [x] **52. Random Delays** - `stealth/delays.py` - Python `time.sleep` - wait 5-20 seconds between each business
- [x] **53. Random User-Agent** - `stealth/user_agent.py` - `fake-useragent` - change User-Agent per request
- [x] **54. Random Headers** - `stealth/headers.py` - Playwright - change Accept-Language, Referer, etc.
- [x] **55. Free Proxy Rotation** - `stealth/proxy_rotation.py` - `proxyscrape.com` API - rotate free IP per request
- [x] **56. GitHub Actions Workflow** - `.github/workflows/findleads.yml` - GitHub Actions - scheduled run every 6 hours (10 min/run)
- [x] **57. GitHub Artifacts** - `.github/workflows/` - GitHub - save `data.duckdb` between runs (auto-delete after 90 days)
- [x] **58. DuckDB Persistence** - `stealth/persistence.py` - DuckDB - save data to single compressed file
- [x] **59. External Backup** - `stealth/backup.py` - Google Drive (15GB) + Dropbox (2GB) - automatic backup via rclone
- [x] **60. IP Rotation Tracking** - `stealth/ip_tracker.py` - track which IPs were used, avoid repeating

---

## ✅ Advanced OSINT (5 algorithms)

- [x] **61. Website Screenshot** - `osint/screenshot.py` - Playwright - screenshot business website (for mockups)
- [x] **62. Page Speed Analysis** - `osint/page_speed.py` - Playwright + Lighthouse - website loading speed
- [x] **63. Mobile Responsiveness Check** - `osint/mobile_check.py` - Playwright - does site work on mobile?
- [x] **64. Social Media Discovery** - `osint/social_media.py` - `requests` + scraping - find social media accounts
- [x] **65. Review Pattern Analysis** - `osint/review_patterns.py` - Python - detect fake reviews

---

## ✅ Parallel Execution Architecture (10 algorithms)

> **The Game Changer**: Run multiple free platforms simultaneously for maximum data collection
> - GitHub Actions + Oracle Cloud + Google Cloud Run + Local Machine
> - Each platform handles different tasks, all feeding into same DuckDB
> - Result: 5.75x more data than single platform

### Platforms Overview

| Platform | Free Tier | Tasks | IPs |
|---|---|---|---|
| **GitHub Actions** | 2000 min/month | Google Maps scraping | Microsoft Azure |
| **Oracle Cloud Free Tier** | 4 ARM VMs + 24GB RAM (ALWAYS FREE) | OSINT + WHOIS + Tech Stack + Sentiment | Oracle |
| **Google Cloud Run** | 2M requests/month | Temporal updates + Change detection | Google |
| **Local Machine** | Unlimited | Monitoring + Reports + Manual | Local |

### Capacity Comparison

| Scenario | Businesses/day | Businesses/month | Cost |
|---|---|---|---|
| **Before (GitHub only)** | 240 | 7,200 | $0 |
| **After (All parallel)** | 1,380 | 41,400 | $0 |

### Algorithms

- [x] **66. Oracle Cloud VM Setup** - `infra/oracle_setup.py` - provision 4 ARM VMs on Oracle Cloud Free Tier (always free, 24GB RAM total)
- [x] **67. Docker Containerization** - `infra/docker.py` - package FindLeads as Docker container for deployment on any platform
- [x] **68. Cloud Sync Engine** - `infra/cloud_sync.py` - sync data.duckdb across all platforms (GitHub Artifacts, Oracle storage, Google Drive)
- [x] **69. Task Distribution Manager** - `infra/task_manager.py` - distribute scraping tasks across platforms (which platform does what)
- [x] **70. IP Pool Manager** - `infra/ip_pool.py` - manage IP addresses from all platforms (Microsoft, Oracle, Google, Local) - avoid repeats
- [x] **71. Health Monitor** - `infra/monitor.py` - monitor all platforms status (is GitHub Actions running? Are Oracle VMs healthy?)
- [x] **72. Auto-Restart** - `infra/auto_restart.py` - auto-restart failed workers on any platform
- [x] **73. Cost Tracker** - `infra/cost_tracker.py` - track usage across all free tiers (GitHub minutes, Oracle CPU, Google requests)
- [x] **74. Data Merge Engine** - `infra/data_merge.py` - merge data from multiple sources into single DuckDB (handle duplicates, conflicts)
- [x] **75. Platform Selector** - `infra/platform_selector.py` - auto-select best platform based on current load and availability

---

## 📊 Progress Summary

| Category | Total | Completed | Remaining |
|---|---|---|---|
| Existing Algorithms | 5 | 5 | 0 |
| Deep OSINT Engine | 8 | 8 | 0 |
| Knowledge Graph (DuckDB + NetworkX) | 7 | 7 | 0 |
| Temporal Tracking & Change Detection | 8 | 8 | 0 |
| Search & Filtering System | 10 | 10 | 0 |
| Stealth & Distribution | 12 | 12 | 0 |
| Parallel Execution Architecture | 10 | 10 | 0 |
| Automated Search & DB Pipeline | 7 | 7 | 0 |
| RLO | 5 | 5 | 0 |
| Autonomous Agent | 5 | 5 | 0 |
| Advanced OSINT | 5 | 5 | 0 |
| **TOTAL** | **75** | **75** | **0** |

---

## 🗄️ Database Architecture

> **Primary**: DuckDB (storage + analytics)
> **Secondary**: NetworkX (graph queries in memory)

### Why DuckDB?
- Embedded (no server, no Docker)
- Columnar storage (compressed, 30-40% of raw size)
- JSON support (tech_stack = ['WordPress', 'WooCommerce'])
- Fast analytics (100x faster than SQLite for OLAP)
- Single file (data.duckdb)
- Free and open source

### Why NetworkX for Graph?
- In-memory graph algorithms (BFS, shortest path, communities)
- Loaded from DuckDB when needed
- Freed after query completes
- Free and open source

### Schema Overview

```sql
-- Businesses
CREATE TABLE businesses (
    id TEXT PRIMARY KEY,
    name TEXT, country TEXT, city TEXT, sector TEXT,
    rating REAL, review_count INTEGER,
    tech_stack TEXT,  -- JSON
    health_score INTEGER,
    created_at DATE, updated_at DATE
);

-- Snapshots (temporal tracking)
CREATE TABLE snapshots (
    id INTEGER PRIMARY KEY,
    business_id TEXT,
    scan_date DATE,
    rating REAL, review_count INTEGER,
    replied_to_reviews INTEGER,
    sentiment_score REAL,
    health_score INTEGER,
    status TEXT  -- 'active', 'declining', 'closed'
);

-- Changes (change detection)
CREATE TABLE changes (
    id INTEGER PRIMARY KEY,
    business_id TEXT,
    scan_date DATE,
    change_type TEXT,  -- 'rating_drop', 'no_reply', 'domain_expiring'
    old_value TEXT, new_value TEXT,
    severity TEXT  -- 'low', 'medium', 'high', 'critical'
);

-- Taxonomy (search filters)
CREATE TABLE taxonomy (
    id INTEGER PRIMARY KEY,
    country TEXT, city TEXT, sector TEXT,
    is_active BOOLEAN,
    last_scan DATE,
    business_count INTEGER,
    avg_health_score REAL
);
```

---

## 📈 Data Growth Projections (6 months)

| Scenario | Businesses/month | After 6 months | Data Size |
|---|---|---|---|
| **Before (GitHub only)** | 7,200 | 43,200 | ~300 MB |
| **After (All parallel)** | 41,400 | 248,400 | ~1.8 GB |

---

## 💰 Total Cost: $0

| Platform | Cost |
|---|---|
| GitHub Actions | $0 (2000 min/month free) |
| Oracle Cloud Free Tier | $0 (4 ARM VMs, 24GB RAM - ALWAYS FREE) |
| Google Cloud Run | $0 (2M requests/month free) |
| DuckDB | $0 (free) |
| NetworkX | $0 (free) |
| Playwright Stealth | $0 (free) |
| TextBlob / VADER | $0 (free) |
| IMAP IDLE | $0 (free) |
| Free Proxies | $0 (free) |
| OpenRouter (llama-3.1-8b:free) | $0 (free) |
| Cal.com | $0 (free) |
| Google Drive Backup | $0 (15GB free) |
| **Total** | **$0** |

---

## 📅 Execution Timeline

| Week | Focus | Algorithms |
|---|---|---|
| Week 1 | Deep OSINT Engine | #6 - #13 |
| Week 2 | Knowledge Graph (DuckDB + NetworkX) | #14 - #20 |
| Week 3 | Temporal Tracking & Change Detection | #21 - #28 |
| Week 4 | Search & Filtering System | #29 - #38 |
| Week 5 | Stealth & Distribution | #49 - #60 |
| Week 6 | **Parallel Execution Architecture** | **#66 - #75** |
| Week 7 | RLO Phase 1 | #39 - #43 |
| Week 8 | Autonomous Agent | #44 - #48 |
| Week 9 | Advanced OSINT + Testing | #61 - #65 |

---

## 🔑 Key Decisions

1. **Database**: DuckDB (storage) + NetworkX (graph queries) — both free, embedded, no server
2. **Parallel Execution**: GitHub Actions + Oracle Cloud + Google Cloud Run + Local — all free, 5.75x more data
3. **Stealth**: Playwright Stealth + GitHub Actions (Microsoft IPs) + Free Proxy Rotation — all free
4. **Learning**: IMAP IDLE + VADER Sentiment — free push notifications + free sentiment analysis
5. **Agent**: LangGraph + Cal.com + llama-3.1-8b:free — free state machine + free scheduling + free LLM
6. **Temporal**: Snapshots + Change Detection — track business health over time
7. **Search**: Multi-criteria filtering (country/city/sector/month/health/rating) — make data actionable
8. **Backup**: GitHub Artifacts (90 days) + Google Drive (15GB) + Dropbox (2GB) — triple redundancy
9. **Oracle Cloud**: 4 ARM VMs ALWAYS FREE — the game changer for 24/7 execution
