-- Reviewer: Add INSERT policy for users table
-- This allows users to create their own profile if the trigger didn't run.

-- Allow users to insert their own profile row
create policy "Users can insert own profile"
on public.users for insert
with check (auth.uid() = id);
