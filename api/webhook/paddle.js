/**
 * POST /api/webhook/paddle
 * Handles Paddle payment webhooks and upgrades user to paid.
 */

import { getSupabaseAdmin } from '../_lib/supabase.js';

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed.' });
  }

  try {
    // TODO: Verify Paddle webhook signature using PADDLE_WEBHOOK_SECRET.
    const event = req.body;
    const eventType = event?.event_type;

    if (eventType !== 'transaction.completed') {
      return res.status(200).json({ received: true, ignored: true });
    }

    const customerEmail = event?.data?.customer?.email;
    const paddleCustomerId = event?.data?.customer?.id;

    if (!customerEmail) {
      return res.status(400).json({ error: 'Missing customer email in webhook payload.' });
    }

    const supabase = getSupabaseAdmin();
    const { error } = await supabase
      .from('users')
      .update({
        is_paid: true,
        paddle_customer_id: paddleCustomerId ?? null,
      })
      .eq('email', customerEmail);

    if (error) {
      return res.status(500).json({ error: 'Failed to update user payment status.' });
    }

    return res.status(200).json({ received: true });
  } catch (error) {
    return res.status(500).json({ error: error.message });
  }
}
