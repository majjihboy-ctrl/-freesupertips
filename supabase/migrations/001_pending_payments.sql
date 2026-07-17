-- Run this in the Supabase SQL editor (Project → SQL Editor → New query).
--
-- Why this table exists:
-- The M-Pesa STK push callback from Safaricom only includes the
-- CheckoutRequestID, phone number, and amount — it does NOT echo back
-- which of your users triggered the payment. Without persisting that
-- link server-side when the payment is initiated, the callback has no
-- reliable way to know whose account to upgrade.

create table if not exists pending_payments (
  id uuid primary key default gen_random_uuid(),
  checkout_request_id text unique not null,
  user_id uuid not null references auth.users(id) on delete cascade,
  amount numeric not null,
  plan text not null, -- 'daily' | 'weekly' | 'monthly'
  status text not null default 'pending', -- 'pending' | 'completed' | 'failed'
  mpesa_receipt text,
  created_at timestamptz not null default now(),
  completed_at timestamptz
);

create index if not exists idx_pending_payments_checkout_request_id
  on pending_payments (checkout_request_id);

-- Make sure your `profiles` table has these columns (adjust if named
-- differently already):
--   is_premium boolean default false
--   premium_until timestamptz

alter table profiles add column if not exists premium_until timestamptz;

-- Row Level Security: only the service role (used by the backend) should
-- read/write this table directly. Users never query it from the client.
alter table pending_payments enable row level security;

drop policy if exists "service role full access" on pending_payments;
create policy "service role full access" on pending_payments
  for all
  using (auth.role() = 'service_role')
  with check (auth.role() = 'service_role');
