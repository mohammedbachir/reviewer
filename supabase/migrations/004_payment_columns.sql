-- Reviewer: Add payment columns to users table
-- Run in Supabase SQL editor

ALTER TABLE public.users
  ADD COLUMN IF NOT EXISTS paddle_customer_id text,
  ADD COLUMN IF NOT EXISTS paddle_transaction_id text,
  ADD COLUMN IF NOT EXISTS subscription_type text,
  ADD COLUMN IF NOT EXISTS paid_at timestamptz;
