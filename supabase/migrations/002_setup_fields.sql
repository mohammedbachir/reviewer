-- Reviewer: Add new setup fields to users table
-- Run in Supabase SQL editor.

-- Add new columns for the setup form
alter table public.users
  add column if not exists sign_off text default '',
  add column if not exists negative_strategy text default 'apologize',
  add column if not exists custom_instructions text default '';
