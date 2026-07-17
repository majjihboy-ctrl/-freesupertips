# FreeSuperTips

Football prediction site: React + TypeScript + Vite frontend, Supabase for
data/auth, `hybrid-scraper.js` populates matches from API-Football + Bzzoiro,
and M-Pesa (Safaricom Daraja) handles premium/VIP payments.

## Setup

1. `npm install`
2. Copy `.env.example` to `.env` and fill in the values (Supabase, API-Football,
   Bzzoiro, M-Pesa, admin emails).
3. Run the SQL migrations in `supabase/migrations/` **in order**, in the
   Supabase SQL editor. `002_match_stats_scheduling_and_overrides.sql` must
   run before the scraper or the admin dashboard will error.
4. `npm run scrape` to populate `match_stats` (yesterday/today/tomorrow).
   Schedule this on a cron (e.g. GitHub Actions, a Vercel Cron Job) — the
   site itself never scrapes on its own.
5. `npm run dev` runs the frontend + local API server together.

## Data flow

`hybrid-scraper.js` → Supabase `match_stats` → `src/api/football.ts` →
`DailyPredictions` / `RecentResults` on the site. The admin dashboard
(`/admin`, gated by `VITE_ADMIN_EMAILS`) edits `admin_prediction`,
`admin_odds`, `admin_confidence`, and `is_premium_override` columns on the
same table — those always take priority over the scraper's own guess.

## Premium / M-Pesa

- `MPESA_ENV=sandbox` (default) only simulates payments. Set
  `MPESA_ENV=production` with real Daraja go-live credentials before
  accepting real money.
- Prices are enforced server-side in `api/_lib/mpesa.js`
  (`PLAN_PRICES_KES`) — the client's plan choice determines the price, not
  a client-supplied amount.
- Payment confirmation is asynchronous: `api/mpesa/stkpush.js` records a
  `pending_payments` row, Safaricom calls `api/mpesa/callback.js` once the
  user enters their PIN, and that's what actually grants `profiles.is_premium`.

## Known limitation: registration emails

Supabase's built-in email sender is rate-limited and often gets marked as
spam — it's not meant for production signup volume. If confirmation emails
aren't arriving, check (in the Supabase dashboard):
- **Authentication → Providers → Email** — confirm "Confirm email" is on
- **Authentication → URL Configuration** — Site URL / Redirect URLs include
  your deployed domain
- **Authentication → Settings → SMTP Settings** — for real production use,
  connect a custom SMTP provider (Resend, SendGrid, etc.) rather than relying
  on Supabase's default sender.
