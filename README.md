# Reviewer

Chrome Extension that injects smart replies on Google Business reviews.

## Project structure

```
reviewer/
├── extension/          # Chrome Extension (Manifest V3)
├── api/                # Vercel serverless functions
├── supabase/           # Database migrations
├── .env.example        # Environment variable template
└── vercel.json         # Vercel config
```

## Current status

- [x] Extension skeleton (`manifest`, `popup`, `content`, `background`)
- [x] API skeleton (`generate-reply`, Paddle webhook)
- [x] Supabase schema migration
- [ ] Supabase OAuth wiring
- [ ] Live DOM selectors for Google Business
- [ ] Paddle checkout links
- [ ] UI design pass
- [ ] Extension icons

## Local setup

### 1. Environment

Copy `.env.example` to `.env` and fill in your keys.

### 2. Supabase

Run `supabase/migrations/001_users.sql` in your Supabase project.

### 3. API (Vercel)

```bash
cd api
npm install
```

Deploy to Vercel and set environment variables from `.env.example`.

### 4. Chrome Extension

1. Open `chrome://extensions`
2. Enable **Developer mode**
3. Click **Load unpacked**
4. Select the `extension/` folder

> Note: Add icon PNGs to `extension/icons/` before publishing (see `extension/icons/README.md`).

## Freemium logic

- 5 free replies per user (`replies_count`)
- After limit: paywall via Paddle ($19/mo or $99 lifetime)
- Paid users: `is_paid = true`, unlimited replies

## Next step

Design pass for popup UI and extension icons — pending approval.
