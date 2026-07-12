/**
 * POST /api/create-checkout
 * Creates a Paddle checkout transaction and returns the checkout URL.
 */

import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
const supabase = createClient(supabaseUrl, supabaseKey);

const PADDLE_API_KEY = process.env.PADDLE_API_KEY;
const PADDLE_SELLER_ID = process.env.PADDLE_SELLER_ID;
const PADDLE_MONTHLY_PRICE_ID = process.env.PADDLE_MONTHLY_PRICE_ID;
const PADDLE_LIFETIME_PRICE_ID = process.env.PADDLE_LIFETIME_PRICE_ID;

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

    const { plan } = req.body;
    if (!plan || !['monthly', 'lifetime'].includes(plan)) {
      return res.status(400).json({ error: 'Invalid plan. Must be "monthly" or "lifetime".' });
    }

    const priceId = plan === 'monthly' ? PADDLE_MONTHLY_PRICE_ID : PADDLE_LIFETIME_PRICE_ID;

    if (!priceId) {
      return res.status(500).json({ error: 'Price not configured.' });
    }

    // Create Paddle transaction (checkout)
    const paddleResponse = await fetch(`${PADDLE_API_URL}/transactions`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${PADDLE_API_KEY}`,
        'Content-Type': 'application/json',
        'Paddle-Version': '1',
      },
      body: JSON.stringify({
        items: [{
          price_id: priceId,
          quantity: 1,
        }],
        customer: {
          email: user.email,
        },
        custom_data: {
          user_id: user.id,
          email: user.email,
        },
      }),
    });

    const paddleData = await paddleResponse.json();

    if (!paddleResponse.ok || !paddleData?.data) {
      console.error('Paddle error:', JSON.stringify(paddleData));
      throw new Error(paddleData?.error?.detail || 'Failed to create checkout.');
    }

    const checkout = paddleData.data;

    return res.status(200).json({
      checkout_url: checkout.checkout?.url || null,
      transaction_id: checkout.id,
      status: checkout.status,
    });

  } catch (error) {
    console.error('Checkout error:', error.message);
    return res.status(500).json({ error: error.message });
  }
}
