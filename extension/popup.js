/**
 * Reviewer — Popup logic
 * Handles Google OAuth via Supabase and user settings.
 */

// Supabase project values
const SUPABASE_URL = 'https://lgbzpwzpkzbquuwwhbin.supabase.co';
const SUPABASE_ANON_KEY = 'sb_publishable_emIKVbAyzrSC7O9za7Gzdg_eVslO14T';

const FREE_REPLY_LIMIT = 5;
const API_BASE = 'https://reviewer-lovat.vercel.app';

// DOM Elements
const authSection = document.getElementById('auth-section');
const settingsSection = document.getElementById('settings-section');
const readySection = document.getElementById('ready-section');
const paywallSection = document.getElementById('paywall-section');
const globalFooter = document.getElementById('global-footer');
const statusMessage = document.getElementById('status-message');
const progressSteps = document.querySelectorAll('.progress-step');
const progressLines = document.querySelectorAll('.progress-line');

const signInBtn = document.getElementById('sign-in-btn');
const signOutBtn = document.getElementById('sign-out-btn');
const saveBtn = document.getElementById('save-btn');
const setupForm = document.getElementById('setup-form');
const editSettingsBtn = document.getElementById('edit-settings-btn');
const upgradeMonthlyBtn = document.getElementById('upgrade-monthly-btn');
const upgradeLifetimeBtn = document.getElementById('upgrade-lifetime-btn');

const userEmailEl = document.getElementById('user-email');
const businessNameInput = document.getElementById('business-name');
const signOffInput = document.getElementById('sign-off');
const toneSelect = document.getElementById('tone');
const negativeStrategySelect = document.getElementById('negative-strategy');
const customInstructionsInput = document.getElementById('custom-instructions');
const usageText = document.getElementById('usage-text');

// --- i18n: Apply translations to all elements with data-i18n ---

function applyTranslations() {
  document.querySelectorAll('[data-i18n]').forEach((el) => {
    const key = el.getAttribute('data-i18n');
    const val = t(key);
    if (val !== key) el.textContent = val;
  });

  document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
    const key = el.getAttribute('data-i18n-placeholder');
    const val = t(key);
    if (val !== key) el.placeholder = val;
  });
}

// --- Supabase Client ---
let supabaseClient = null;

function getSupabase() {
  if (supabaseClient) return supabaseClient;
  if (!SUPABASE_URL || !SUPABASE_ANON_KEY || !window.supabase) return null;
  supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
  return supabaseClient;
}

// --- UI Helpers ---

function setStatus(message, isError = false) {
  statusMessage.textContent = message;
  statusMessage.classList.toggle('is-error', isError);
}

function updateProgress(activeView) {
  const order = ['auth', 'setup', 'ready'];
  const activeIndex = order.indexOf(activeView);

  progressSteps.forEach((step, index) => {
    step.classList.remove('is-active', 'is-complete');
    if (index < activeIndex) {
      step.classList.add('is-complete');
    } else if (index === activeIndex) {
      step.classList.add('is-active');
    }
  });

  progressLines.forEach((line, index) => {
    line.classList.toggle('is-complete', index < activeIndex);
  });
}

function showSection(section) {
  authSection.hidden = section !== 'auth';
  settingsSection.hidden = section !== 'setup';
  readySection.hidden = section !== 'ready';
  paywallSection.hidden = section !== 'paywall';

  globalFooter.hidden = section === 'auth';
  updateProgress(section === 'paywall' ? 'ready' : section);
}

function isSetupComplete(user) {
  return Boolean(user?.business_name?.trim());
}

// --- Local Storage ---

async function getLocalUser() {
  const { user } = await chrome.storage.local.get('user');
  return user ?? null;
}

async function saveLocalUser(user) {
  await chrome.storage.local.set({ user });
}

async function clearLocalUser() {
  await chrome.storage.local.remove('user');
}

// --- UI Updates ---

function updateUsageText(user) {
  if (user.is_paid) {
    usageText.textContent = t('planPro');
    return;
  }

  const remaining = Math.max(FREE_REPLY_LIMIT - (user.replies_count ?? 0), 0);
  usageText.textContent = t('freeRepliesLeft')(remaining);
}

function hydrateSettingsForm(user) {
  userEmailEl.textContent = user.email ?? '';
  businessNameInput.value = user.business_name ?? '';
  signOffInput.value = user.sign_off ?? '';
  toneSelect.value = user.tone ?? 'friendly';
  negativeStrategySelect.value = user.negative_strategy ?? 'apologize';
  customInstructionsInput.value = user.custom_instructions ?? '';
}

// --- Render (simple, no blocking async calls) ---

function render() {
  const user = getLocalUserFromCache();

  if (!user) {
    showSection('auth');
    return;
  }

  if (!user.is_paid && user.replies_count >= FREE_REPLY_LIMIT) {
    showSection('paywall');
    return;
  }

  if (isSetupComplete(user)) {
    updateUsageText(user);
    showSection('ready');
    return;
  }

  showSection('setup');
  hydrateSettingsForm(user);
}

// Cache for synchronous access
let _cachedUser = null;

function getLocalUserFromCache() {
  return _cachedUser;
}

async function loadAndRender() {
  _cachedUser = await getLocalUser();
  render();

  // Background: check Supabase for fresh payment status (non-blocking)
  if (_cachedUser?.access_token) {
    syncPaymentStatus();
  }
}

async function syncPaymentStatus() {
  try {
    const { user } = await chrome.storage.local.get('user');
    if (!user?.access_token) return;

    // Call check-payment API which checks BOTH Supabase AND Paddle API
    const res = await fetch(`${API_BASE}/api/check-payment`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${user.access_token}`,
      },
    });

    const data = await res.json();

    if (data.is_paid && !user.is_paid) {
      const updatedUser = {
        ...user,
        is_paid: true,
        subscription_type: data.subscription_type,
      };
      await saveLocalUser(updatedUser);
      _cachedUser = updatedUser;
      render();
    }
  } catch (e) {
    console.warn('[Reviewer] Payment sync skipped:', e.message);
  }
}

function setSaveLoading(isLoading) {
  saveBtn.disabled = isLoading;
  saveBtn.classList.toggle('is-loading', isLoading);
}

// --- Auth (Supabase Google OAuth) ---

function signInWithGoogle() {
  setStatus(t('signInGoogle') + '...');
  signInBtn.disabled = true;

  const redirectUri = chrome.identity.getRedirectURL();
  const authUrl = `${SUPABASE_URL}/auth/v1/authorize?provider=google&redirect_to=${encodeURIComponent(redirectUri)}`;

  chrome.identity.launchWebAuthFlow(
    {
      url: authUrl,
      interactive: true,
    },
    async (redirectUrl) => {
      if (chrome.runtime.lastError || !redirectUrl) {
        const msg = chrome.runtime.lastError?.message || 'Sign-in was cancelled.';
        setStatus(msg, true);
        signInBtn.disabled = false;
        return;
      }

      try {
        const url = new URL(redirectUrl);
        const rawHash = url.hash.substring(1);
        const rawQuery = url.search.substring(1);
        const combined = rawHash || rawQuery;
        const params = new URLSearchParams(combined);

        const accessToken = params.get('access_token');
        const refreshToken = params.get('refresh_token');

        if (!accessToken || !refreshToken) {
          throw new Error('No tokens received from auth.');
        }

        const payload = JSON.parse(atob(accessToken.split('.')[1]));

        // Check if user already has settings from a previous session
        const existingUser = await getLocalUser();
        const existingSettings = existingUser?.id === payload.sub ? {
          business_name: existingUser.business_name,
          sign_off: existingUser.sign_off,
          tone: existingUser.tone,
          negative_strategy: existingUser.negative_strategy,
          custom_instructions: existingUser.custom_instructions,
          replies_count: existingUser.replies_count,
          is_paid: existingUser.is_paid,
        } : {};

        const localUser = {
          id: payload.sub,
          email: payload.email || '',
          access_token: accessToken,
          refresh_token: refreshToken,
          replies_count: existingSettings.replies_count ?? 0,
          is_paid: existingSettings.is_paid ?? false,
          business_name: existingSettings.business_name ?? '',
          sign_off: existingSettings.sign_off ?? '',
          tone: existingSettings.tone ?? 'friendly',
          negative_strategy: existingSettings.negative_strategy ?? 'apologize',
          custom_instructions: existingSettings.custom_instructions ?? '',
        };

        await saveLocalUser(localUser);
        _cachedUser = localUser;
        setStatus('');
        signInBtn.disabled = false;
        render();
      } catch (err) {
        setStatus(err.message || 'Failed to complete sign-in.', true);
        signInBtn.disabled = false;
      }
    }
  );
}

async function signOut() {
  try {
    const client = getSupabase();
    if (client) {
      const { user } = await chrome.storage.local.get('user');
      if (user?.access_token && user?.refresh_token) {
        await client.auth.setSession({
          access_token: user.access_token,
          refresh_token: user.refresh_token,
        });
        await client.auth.signOut();
      }
    }
  } catch (err) {
    console.warn('[Reviewer] Sign out error (non-fatal):', err.message);
  }

  await clearLocalUser();
  _cachedUser = null;
  render();
}

// --- Settings ---

async function saveSettings(event) {
  event.preventDefault();

  const businessName = businessNameInput.value.trim();
  if (!businessName) {
    setStatus(t('enterBusinessName'), true);
    businessNameInput.focus();
    return;
  }

  const user = await getLocalUser();
  if (!user) return;

  setSaveLoading(true);
  setStatus('');

  const settings = {
    business_name: businessName,
    sign_off: signOffInput.value.trim(),
    tone: toneSelect.value,
    negative_strategy: negativeStrategySelect.value,
    custom_instructions: customInstructionsInput.value.trim(),
    is_configured: true,
  };

  const updatedUser = { ...user, ...settings };
  await saveLocalUser(updatedUser);
  _cachedUser = updatedUser;

  // Upsert to Supabase (best-effort)
  try {
    const client = getSupabase();
    if (client && user.access_token && user.refresh_token) {
      await client.auth.setSession({
        access_token: user.access_token,
        refresh_token: user.refresh_token,
      });
      const { error } = await client
        .from('users')
        .upsert({
          id: user.id,
          email: user.email,
          business_name: settings.business_name,
          sign_off: settings.sign_off,
          tone: settings.tone,
          negative_strategy: settings.negative_strategy,
          custom_instructions: settings.custom_instructions,
        }, { onConflict: 'id' });

      if (error) console.warn('[Reviewer] Supabase upsert skipped:', error.message);
    }
  } catch (err) {
    console.warn('[Reviewer] Supabase upsert skipped:', err.message);
  }

  setSaveLoading(false);
  setStatus('');
  render();
}

// --- Paywall ---

async function openCheckout(plan) {
  const user = await getLocalUser();
  if (!user?.access_token) {
    setStatus(t('pleaseSignIn'), true);
    return;
  }

  // Ensure we have a fresh token
  let freshToken = user.access_token;
  try {
    const client = getSupabase();
    if (client) {
      await client.auth.setSession({
        access_token: user.access_token,
        refresh_token: user.refresh_token,
      });
      const { data } = await client.auth.getSession();
      if (data?.session?.access_token) {
        freshToken = data.session.access_token;
      }
    }
  } catch (e) {
    console.warn('[Reviewer] Session refresh failed:', e.message);
  }

  setStatus(t('openingCheckout')(plan));
  upgradeMonthlyBtn.disabled = true;
  upgradeLifetimeBtn.disabled = true;

  try {
    const response = await fetch(`${API_BASE}/api/create-checkout`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${freshToken}`,
      },
      body: JSON.stringify({ plan }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || 'Failed to create checkout.');
    }

    if (data.checkout_url) {
      // Open OUR index.html with the transaction ID (not Paddle's hosted page)
      // This way Paddle.Checkout.open() runs in our page and we catch Paddle.Completed
      const checkoutPage = `${API_BASE}/?_ptxn=${data.transaction_id}`;
      chrome.tabs.create({ url: checkoutPage });
      setStatus(t('checkoutOpened'));

      // Poll for payment status every 5 seconds for up to 2 minutes
      startPaymentPoll(freshToken);
    } else {
      throw new Error('No checkout URL received.');
    }
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    upgradeMonthlyBtn.disabled = false;
    upgradeLifetimeBtn.disabled = false;
  }
}

// Poll for payment status after checkout
let _paymentPollTimer = null;

function startPaymentPoll(token) {
  if (_paymentPollTimer) clearInterval(_paymentPollTimer);

  let attempts = 0;
  const maxAttempts = 24; // 24 * 5s = 2 minutes

  _paymentPollTimer = setInterval(async () => {
    attempts++;
    if (attempts > maxAttempts) {
      clearInterval(_paymentPollTimer);
      _paymentPollTimer = null;
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/api/check-payment`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
      });

      const data = await res.json();

      if (data.is_paid) {
        clearInterval(_paymentPollTimer);
        _paymentPollTimer = null;

        // Update local user
        const localUser = await getLocalUser();
        if (localUser) {
          const updatedUser = {
            ...localUser,
            is_paid: true,
            subscription_type: data.subscription_type,
          };
          await saveLocalUser(updatedUser);
          _cachedUser = updatedUser;
          render();
        }

        setStatus(t('checkoutOpened'));
      }
    } catch (e) {
      // Silently continue polling
    }
  }, 5000);
}

// --- Events ---

signInBtn.addEventListener('click', signInWithGoogle);
signOutBtn.addEventListener('click', signOut);
setupForm.addEventListener('submit', saveSettings);
editSettingsBtn.addEventListener('click', () => {
  const user = getLocalUserFromCache();
  if (!user) return;
  showSection('setup');
  hydrateSettingsForm(user);
});
upgradeMonthlyBtn.addEventListener('click', () => openCheckout('monthly'));
upgradeLifetimeBtn.addEventListener('click', () => openCheckout('lifetime'));

// Initialize
applyTranslations();
loadAndRender();
