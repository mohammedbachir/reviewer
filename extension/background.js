/**
 * Reviewer — Background service worker (Manifest V3)
 * Routes API calls from content script and keeps auth token in sync.
 */

const API_BASE_URL = ''; // TODO: Set Vercel deployment URL, e.g. https://reviewer.vercel.app

// Handle messages from content script and callback page
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === 'GENERATE_REPLY') {
    handleGenerateReply(message.payload)
      .then(sendResponse)
      .catch((error) => {
        sendResponse({ ok: false, error: error.message });
      });
    return true;
  }

  if (message?.type === 'AUTH_SUCCESS') {
    handleAuthSuccess(message.payload)
      .then(() => sendResponse({ ok: true }))
      .catch((error) => sendResponse({ ok: false, error: error.message }));
    return true;
  }

  return false;
});

// Handle successful auth from callback page
async function handleAuthSuccess({ accessToken, refreshToken }) {
  // Decode user info from JWT
  const payload = JSON.parse(atob(accessToken.split('.')[1]));

  const localUser = {
    id: payload.sub,
    email: payload.email || '',
    access_token: accessToken,
    refresh_token: refreshToken,
    replies_count: 0,
    is_paid: false,
    business_name: '',
    tone: 'professional',
  };

  await chrome.storage.local.set({ user: localUser });
}

// Generate reply using the API
async function handleGenerateReply(payload) {
  const { user } = await chrome.storage.local.get('user');

  if (!user?.access_token) {
    throw new Error('Please sign in from the extension popup.');
  }

  if (!API_BASE_URL) {
    throw new Error('API URL is not configured in background.js.');
  }

  const response = await fetch(`${API_BASE_URL}/api/generate-reply`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${user.access_token}`,
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error ?? 'Failed to generate reply.');
  }

  // Keep local usage count in sync after a successful reply.
  if (typeof data.replies_count === 'number') {
    await chrome.storage.local.set({
      user: { ...user, replies_count: data.replies_count },
    });
  }

  return { ok: true, reply: data.reply };
}

// Handle extension install
chrome.runtime.onInstalled.addListener(() => {
  console.log('Reviewer extension installed');
});
