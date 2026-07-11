/**
 * Verify Supabase JWT from Authorization header.
 */

import { createClient } from '@supabase/supabase-js';

export async function verifyAuth(req) {
  const authHeader = req.headers.authorization ?? req.headers.Authorization;

  if (!authHeader?.startsWith('Bearer ')) {
    throw new Error('Missing or invalid Authorization header.');
  }

  const token = authHeader.slice(7);
  const url = process.env.SUPABASE_URL;
  const anonKey = process.env.SUPABASE_ANON_KEY;

  if (!url || !anonKey) {
    throw new Error('Missing Supabase auth environment variables.');
  }

  const supabase = createClient(url, anonKey);
  const { data, error } = await supabase.auth.getUser(token);

  if (error || !data.user) {
    throw new Error('Invalid or expired session.');
  }

  return data.user;
}
