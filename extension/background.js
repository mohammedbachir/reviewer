/**
 * Reviewer — Background service worker (Manifest V3)
 * Routes API calls from content script, keeps auth tokens fresh,
 * and handles Paddle checkout redirects.
 */

const API_BASE_URL = 'https://reviewer-lovat.vercel.app';
const SUPABASE_URL = 'https://lgbzpwzpkzbquuwwhbin.supabase.co';
const SUPABASE_ANON_KEY = 'sb_publishable_emIKVbAyzrSC7O9za7Gzdg_eVslO14T';

// ─── Message Router ─────────────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === 'GENERATE_REPLY') {
    handleGenerateReply(message.payload)
      .then(sendResponse)
      .catch((error) => sendResponse({ ok: false, error: error.message }));
    return true;
  }

  if (message?.type === 'AUTH_SUCCESS') {
    handleAuthSuccess(message.payload)
      .then(() => sendResponse({ ok: true }))
      .catch((error) => sendResponse({ ok: false, error: error.message }));
    return true;
  }

  if (message?.type === 'OPEN_CHECKOUT') {
    handleOpenCheckout(message.payload)
      .then(sendResponse)
      .catch((error) => sendResponse({ ok: false, error: error.message }));
    return true;
  }

  return false;
});

// ─── Token Management ───────────────────────────────────────────────────────

async function refreshAccessToken(user) {
  if (!user?.refresh_token) return null;

  try {
    const res = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=refresh_token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        apikey: SUPABASE_ANON_KEY,
      },
      body: JSON.stringify({ refresh_token: user.refresh_token }),
    });

    const data = await res.json();

    if (data.access_token && data.refresh_token) {
      const updatedUser = {
        ...user,
        access_token: data.access_token,
        refresh_token: data.refresh_token,
      };
      await chrome.storage.local.set({ user: updatedUser });
      return updatedUser;
    }

    console.error('[Reviewer] Token refresh failed:', data);
    return null;
  } catch (err) {
    console.error('[Reviewer] Token refresh error:', err);
    return null;
  }
}

async function getValidToken(user) {
  if (user?.access_token) {
    try {
      const payload = JSON.parse(atob(user.access_token.split('.')[1]));
      const expiresAt = payload.exp * 1000;
      const now = Date.now();
      const buffer = 60 * 1000;

      if (expiresAt - now > buffer) {
        return user.access_token;
      }
    } catch {
      // Could not decode — attempt refresh anyway
    }
  }

  const refreshed = await refreshAccessToken(user);
  return refreshed?.access_token ?? null;
}

// ─── Auth Success (from OAuth callback) ─────────────────────────────────────

async function handleAuthSuccess({ accessToken, refreshToken }) {
  const payload = JSON.parse(atob(accessToken.split('.')[1]));

  const localUser = {
    id: payload.sub,
    email: payload.email || '',
    access_token: accessToken,
    refresh_token: refreshToken,
    replies_count: 0,
    is_paid: false,
    business_name: '',
    sign_off: '',
    tone: 'friendly',
    negative_strategy: 'apologize',
    custom_instructions: '',
  };

  await chrome.storage.local.set({ user: localUser });
}

// ─── Generate Reply ─────────────────────────────────────────────────────────

async function handleGenerateReply(payload) {
  let { user } = await chrome.storage.local.get('user');

  if (!user?.access_token) {
    throw new Error('Please sign in from the extension popup.');
  }

  const token = await getValidToken(user);
  if (!token) {
    throw new Error('Session expired. Please sign in again from the popup.');
  }

  const response = await fetch(`${API_BASE_URL}/api/generate-reply`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json();

  // Pass through PAYWALL error so content.js can handle the redirect
  if (!response.ok) {
    throw new Error(data.error ?? 'Failed to generate reply.');
  }

  if (typeof data.replies_count === 'number') {
    await chrome.storage.local.set({
      user: { ...user, replies_count: data.replies_count },
    });
  }

  return { ok: true, reply: data.reply };
}

// ─── Paddle Checkout ────────────────────────────────────────────────────────

async function handleOpenCheckout({ email }) {
  if (!email) throw new Error('No user email found.');

  let { user } = await chrome.storage.local.get('user');

  // Ensure we have a fresh token for the API call
  let token = user?.access_token;
  if (user) {
    token = await getValidToken(user);
  }

  if (!token) throw new Error('Session expired. Please sign in again.');

  const res = await fetch(`${API_BASE_URL}/api/create-checkout`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ plan: 'lifetime' }),
  });

  const data = await res.json();

  if (!res.ok) throw new Error(data.error || 'Failed to create checkout.');

  if (data.checkout_url) {
    chrome.tabs.create({ url: data.checkout_url });
    return { ok: true };
  }

  throw new Error('No checkout URL received.');
}

// ─── Install ────────────────────────────────────────────────────────────────

chrome.runtime.onInstalled.addListener(() => {
  console.log('Reviewer extension installed');
});
