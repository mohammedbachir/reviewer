# FindLeads — Deployment Guide

## Quick Start: Hugging Face Spaces (Recommended — 100% Free)

### Step 1: Create Hugging Face Account
1. Go to: https://huggingface.co/join
2. Sign up with email
3. Verify your email

### Step 2: Create a New Space
1. Go to: https://huggingface.co/new-space
2. Fill in:
   - **Space name:** `findleads-scraper`
   - **License:** `apache-2.0`
   - **SDK:** `Docker`
   - **Visibility:** `Public` or `Private`
3. Click **"Create Space"**

### Step 3: Upload Files
1. In your new Space, go to **"Files"** tab
2. Click **"Add file" → "Upload files"**
3. Upload these files:
   - `app.py`
   - `Dockerfile`
   - `.dockerignore`
   - `requirements.txt`
   - `lead-generator/` folder (entire folder)
4. Click **"Commit changes"**

### Step 4: Wait for Build
- Hugging Face will automatically build your Docker container
- Takes 5-10 minutes first time
- Go to **"Logs"** tab to watch progress

### Step 5: Done!
- Your scraper is now running 24/7
- Every 6 hours it scrapes new data
- Visit `https://your-username-findleads-scraper.hf.space/stats` to see results

---

## Alternative: Render (Free Tier)

### Step 1: Create Render Account
1. Go to: https://render.com/register
2. Sign up with GitHub

### Step 2: Create New Service
1. Click **"New" → "Background Worker"**
2. Connect your GitHub repo
3. Render will auto-detect `render.yaml`
4. Click **"Create Background Worker"**

### Step 3: Done!
- Render runs your scraper 24/7
- Free tier: 512MB RAM (enough for our scraper)
- Logs available in Render dashboard

---

## Alternative: Run Locally

### Step 1: Install Python
```bash
# Windows
winget install Python.Python.3.12

# Mac
brew install python@3.12

# Linux
sudo apt install python3-pip
```

### Step 2: Install Dependencies
```bash
cd reviewer
pip install -r requirements.txt
playwright install chromium --with-deps
```

### Step 3: Run
```bash
# Single run
python lead-generator/pipeline/orchestrator.py --city "Dubai" --sector "beauty salon" --limit 10

# Multi-city
python lead-generator/pipeline/orchestrator.py --multi-city --limit 10

# Scheduled (runs every 6 hours)
python app.py
```

---

## Environment Variables (Optional)

If you want email sending and AI features, set these:

### Hugging Face
1. Go to your Space → **"Settings"** → **"Repository secrets"**
2. Add:
   - `OPENROUTER_API_KEY` = your key
   - `GMAIL_USER` = your email
   - `GMAIL_PASS` = your app password

### Render
1. Go to your service → **"Environment"**
2. Add the same variables

---

## Monitoring

### Check if it's running:
```bash
# Hugging Face
curl https://your-username-findleads-scraper.hf.space/health

# Render
curl https://your-service.onrender.com/health

# Local
curl http://localhost:7860/health
```

### Check statistics:
```bash
curl https://your-username-findleads-scraper.hf.space/stats
```

---

## Troubleshooting

### "Playwright not found"
```bash
playwright install chromium --with-deps
```

### "Module not found"
```bash
pip install -r requirements.txt
```

### "Database locked"
- Stop all running instances
- Delete `data.duckdb` and let it recreate

### Build fails on Hugging Face
- Check the **"Logs"** tab
- Make sure all files are uploaded
- Ensure `Dockerfile` is in the root directory
