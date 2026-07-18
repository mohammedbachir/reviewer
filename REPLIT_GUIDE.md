# FindLeads — Replit + UptimeRobot Setup Guide

## Step 1: Create Replit Account
1. Go to: https://replit.com/signup
2. Sign up with Google (Gmail)
3. Create a new Repl:
   - Language: Python
   - Template: Flask
   - Name: findleads-scraper

## Step 2: Upload Files
1. In your Repl, upload these files:
   - `replit_main.py`
   - `replit.nix`
   - `.replit`
   - `requirements.txt`
   - `lead-generator/` folder (entire folder)

## Step 3: Run
1. Click the green "Run" button
2. Wait for dependencies to install
3. You'll see "FindLeads Scraper" running
4. Copy the URL (looks like: `https://findleads-scraper.yourusername.repl.co`)

## Step 4: Setup UptimeRobot (Keeps It Alive 24/7)
1. Go to: https://uptimerobot.com/signup
2. Create a free account
3. Click "Add New Monitor"
4. Fill in:
   - Monitor Type: HTTP(s)
   - Friendly Name: FindLeads
   - URL: (paste your Replit URL)
   - Monitoring Interval: 5 minutes
5. Click "Create Monitor"

## Step 5: Done!
- UptimeRobot pings your Replit every 5 minutes
- Replit thinks someone is visiting
- Script runs 24/7 without stopping
- FREE forever!

## How to Update Code
1. Edit files in Replit
2. Click "Run" again
3. Changes apply immediately

## How to Check Logs
- In Replit, click "Shell" tab
- You'll see scraper output
- Check `/stats` endpoint for database stats

## Cost: $0
- Replit: Free
- UptimeRobot: Free
- No credit card needed
