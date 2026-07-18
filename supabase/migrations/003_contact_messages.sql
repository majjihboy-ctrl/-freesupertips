-- Run this in the Supabase SQL editor (Project → SQL Editor → New query).
--
-- Contact form submissions (Contact page). Anyone (including anonymous
-- visitors) can submit; only you can read them via the Supabase dashboard
-- (Table Editor) or a future admin view.

create table if not exists contact_messages (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  email text not null,
  message text not null,
  created_at timestamptz not null default now()
);

alter table contact_messages enable row level security;

drop policy if exists "anyone can submit" on contact_messages;
create policy "anyone can submit" on contact_messages
  for insert
  with check (true);

drop policy if exists "service role can read" on contact_messages;
create policy "service role can read" on contact_messages
  for select
  using (auth.role() = 'service_role');
