-- Reviewer: users table
-- Run in Supabase SQL editor or via migration tooling.

create table if not exists public.users (
  id uuid primary key references auth.users (id) on delete cascade,
  email text not null unique,
  business_name text,
  tone text default 'professional',
  replies_count smallint not null default 0,
  is_paid boolean not null default false,
  paddle_customer_id text,
  created_at timestamptz not null default now()
);

-- Auto-create profile row when a new auth user signs up.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.users (id, email)
  values (new.id, new.email)
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;

create trigger on_auth_user_created
after insert on auth.users
for each row execute function public.handle_new_user();

-- Row Level Security
alter table public.users enable row level security;

create policy "Users can read own profile"
on public.users for select
using (auth.uid() = id);

create policy "Users can update own profile"
on public.users for update
using (auth.uid() = id);
