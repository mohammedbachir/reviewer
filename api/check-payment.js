/**
 * POST /api/check-payment
 * Lets the extension poll for payment status after checkout.
 * Uses Paddle API to look up transaction by user email.
 */

import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
const supabase = createClient(supabaseUrl, supabaseKey);

const PADDLE_API_KEY = process.env.PADDLE_API_KEY;

const PADDLE_API_URL = PADDLE_API_KEY?.includes('_sdbx_')
  ? 'https://sandbox-api.paddle.com'
  : 'https://api.paddle.com';

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed.' });
  }

  try {
    const authHeader = req.headers.authorization;
    const token = authHeader ? authHeader.replace('Bearer ', '') : null;

    if (!token) {
      return res.status(401).json({ error: 'Unauthorized.' });
    }

    const { data: { user }, error: userError } = await supabase.auth.getUser(token);
    if (userError || !user) {
      return res.status(401).json({ error: 'Invalid token.' });
    }

    // Check Supabase for payment status
    const { data: profile } = await supabase
      .from('users')
      .select('is_paid, subscription_type, replies_count')
      .eq('id', user.id)
      .single();

    if (!profile) {
      return res.status(200).json({ is_paid: false });
    }

    // If already marked as paid in DB, return immediately
    if (profile.is_paid) {
      return res.status(200).json({
        is_paid: true,
        subscription_type: profile.subscription_type,
      });
    }

    // Not yet paid — check Paddle for completed transactions by email
    try {
      const paddleRes = await fetch(
        `${PADDLE_API_URL}/transactions?email=${encodeURIComponent(user.email)}&status=completed&limit=5`,
        {
          headers: {
            'Authorization': `Bearer ${PADDLE_API_KEY}`,
            'Content-Type': 'application/json',
          },
        }
      );

      const paddleData = await paddleRes.json();

      if (paddleRes.ok && paddleData?.data?.length > 0) {
        // Found a completed transaction — upgrade user
        const txn = paddleData.data[0];
        const updateData = {
          is_paid: true,
          paddle_customer_id: txn.customer?.id || null,
          paddle_transaction_id: txn.id || null,
          subscription_type: txn.billing?.type === 'subscription' ? 'monthly' : 'lifetime',
          paid_at: new Date().toISOString(),
        };

        await supabase
          .from('users')
          .update(updateData)
          .eq('id', user.id);

        return res.status(200).json({
          is_paid: true,
          subscription_type: updateData.subscription_type,
        });
      }
    } catch (paddleErr) {
      console.warn('[check-payment] Paddle lookup failed:', paddleErr.message);
    }

    return res.status(200).json({ is_paid: false });

  } catch (error) {
    console.error('[check-payment] Error:', error.message);
    return res.status(200).json({ is_paid: false });
  }
}
