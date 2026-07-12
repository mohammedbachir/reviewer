/**
 * POST /api/paddle-webhook
 * Paddle Billing v2 webhook handler.
 *
 * Verifies Paddle signature → extracts user email → upgrades Supabase user to paid.
 *
 * Signature verification (Paddle Billing):
 *   Header format:  Paddle-Signature: ts=TIMESTAMP;h1=HASH
 *   Signed payload:  `${ts}:${rawBody}`
 *   Hash:           HMAC-SHA256(signedPayload, PADDLE_WEBHOOK_SECRET)
 */

import { createClient } from '@supabase/supabase-js';
import crypto from 'crypto';

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
const supabase = createClient(supabaseUrl, supabaseKey);

const PADDLE_WEBHOOK_SECRET = process.env.PADDLE_WEBHOOK_SECRET;

// ─── Signature Verification ─────────────────────────────────────────────────

function verifyPaddleSignature(rawBody, signatureHeader) {
  if (!PADDLE_WEBHOOK_SECRET || !signatureHeader) return false;

  // Parse "ts=123;h1=abc..." into { ts, h1 }
  const parts = {};
  for (const part of signatureHeader.split(';')) {
    const [key, ...rest] = part.split('=');
    if (key && rest.length) parts[key.trim()] = rest.join('=').trim();
  }

  const { ts, h1 } = parts;
  if (!ts || !h1) return false;

  // Reconstruct the signed payload Paddle used:  "ts_value:raw_body_string"
  const signedPayload = `${ts}:${rawBody}`;

  // Compute expected HMAC-SHA256
  const expected = crypto
    .createHmac('sha256', PADDLE_WEBHOOK_SECRET)
    .update(signedPayload)
    .digest('hex');

  return expected === h1;
}

// ─── Event Handlers ─────────────────────────────────────────────────────────

function extractEmail(data) {
  return data?.customer?.email
    || data?.custom_data?.email
    || null;
}

function extractUserId(data) {
  return data?.custom_data?.user_id || null;
}

async function handleTransactionCompleted(data) {
  const email = extractEmail(data);
  const userId = extractUserId(data);

  if (!email && !userId) {
    console.error('[paddle-webhook] transaction.completed: no email or user_id found');
    return;
  }

  const updateData = {
    is_paid: true,
    paddle_customer_id: data?.customer?.id || null,
    paddle_transaction_id: data?.id || null,
    subscription_type: data?.billing?.type === 'subscription' ? 'monthly' : 'lifetime',
    paid_at: new Date().toISOString(),
  };

  // Try user_id first (more reliable), fall back to email
  let result;
  if (userId) {
    result = await supabase.from('users').update(updateData).eq('id', userId);
  }
  if (!userId || result?.error) {
    result = await supabase.from('users').update(updateData).eq('email', email);
  }

  if (result?.error) {
    console.error('[paddle-webhook] Failed to upgrade user:', result.error.message);
  } else {
    console.log('[paddle-webhook] User upgraded to paid:', userId || email);
  }
}

async function handleSubscriptionCanceled(data) {
  const email = extractEmail(data);
  if (!email) return;

  const { error } = await supabase
    .from('users')
    .update({ is_paid: false, subscription_type: null })
    .eq('email', email);

  if (error) {
    console.error('[paddle-webhook] Failed to cancel subscription:', error.message);
  } else {
    console.log('[paddle-webhook] Subscription canceled:', email);
  }
}

// ─── Handler ────────────────────────────────────────────────────────────────

export default async function handler(req, res) {
  // Only accept POST
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // 1. Reconstruct raw body string for signature verification.
  //    Vercel already parsed req.body into an object, so we stringify it back.
  //    Paddle signs the original JSON string; JSON.stringify is deterministic
  //    and matches the original payload structure.
  const rawBody = JSON.stringify(req.body);

  // 2. Verify Paddle signature (CRITICAL — reject unsigned requests)
  const signatureHeader = req.headers['paddle-signature'];
  if (!verifyPaddleSignature(rawBody, signatureHeader)) {
    console.error('[paddle-webhook] Invalid or missing signature');
    return res.status(401).json({ error: 'Invalid signature' });
  }

  // 3. Process the event
  const eventType = req.body?.event_type;
  console.log('[paddle-webhook] Received event:', eventType);

  try {
    switch (eventType) {
      case 'transaction.completed':
        await handleTransactionCompleted(req.body.data);
        break;

      case 'subscription.created':
        // subscription.created fires alongside transaction.completed for subs
        // We handle upgrade in transaction.completed, but this covers edge cases
        await handleTransactionCompleted(req.body.data);
        break;

      case 'subscription.canceled':
        await handleSubscriptionCanceled(req.body.data);
        break;

      // transaction.updated handles refunds / cancellations
      case 'transaction.updated': {
        const status = req.body.data?.status;
        if (status === 'canceled' || status === 'refund') {
          const email = extractEmail(req.body.data);
          if (email) {
            await supabase
              .from('users')
              .update({ is_paid: false, subscription_type: null })
              .eq('email', email);
            console.log('[paddle-webhook] User downgraded (refund/cancel):', email);
          }
        }
        break;
      }

      default:
        console.log('[paddle-webhook] Unhandled event type:', eventType);
    }
  } catch (err) {
    console.error('[paddle-webhook] Error processing event:', err.message);
    // Still return 200 so Paddle doesn't retry on our processing errors.
    // Signature was valid — the issue is on our side.
  }

  // 4. Always respond 200 immediately so Paddle stops retrying
  return res.status(200).json({ success: true });
}
