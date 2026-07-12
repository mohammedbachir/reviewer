/**
 * Reviewer — Popup logic
 * Handles Google OAuth via Supabase and user settings.
 */

// Supabase project values
const SUPABASE_URL = 'https://lgbzpwzpkzbquuwwhbin.supabase.co';
const SUPABASE_ANON_KEY = 'sb_publishable_emIKVbAyzrSC7O9za7Gzdg_eVslO14T';

const FREE_REPLY_LIMIT = 5;

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

async function initSupabase() {
  if (supabaseClient) return supabaseClient;

  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    console.warn('Supabase credentials not configured');
    return null;
  }

  supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

  // Restore session from storage
  const { user } = await chrome.storage.local.get('user');
  if (user?.access_token && user?.refresh_token) {
    try {
      const { data, error } = await supabaseClient.auth.setSession({
        access_token: user.access_token,
        refresh_token: user.refresh_token,
      });

      // Save refreshed tokens back to storage
      if (data?.session?.access_token) {
        await saveLocalUser({
          ...user,
          access_token: data.session.access_token,
          refresh_token: data.session.refresh_token,
        });
      }
    } catch (e) {
      console.warn('Failed to restore Supabase session:', e.message);
    }
  }

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

async function render() {
  const user = await getLocalUser();

  if (!user) {
    showSection('auth');
    return;
  }

  // Re-check payment status from Supabase (in case webhook upgraded user)
  if (user.access_token && user.refresh_token) {
    try {
      const client = await initSupabase();
      if (client) {
        const { data: { user: authUser } } = await client.auth.getUser();
        if (authUser) {
          const { data: profile } = await client
            .from('users')
            .select('is_paid, subscription_type, replies_count')
            .eq('id', authUser.id)
            .single();

          if (profile && (profile.is_paid !== user.is_paid || profile.replies_count !== user.replies_count)) {
            const updatedUser = {
              ...user,
              is_paid: profile.is_paid,
              subscription_type: profile.subscription_type,
              replies_count: profile.replies_count,
            };
            await saveLocalUser(updatedUser);
            return render(); // re-render with fresh data
          }
        }
      }
    } catch (e) {
      console.warn('[Reviewer] Payment status check skipped:', e.message);
    }
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

        await saveLocalUser(localUser);
        setStatus('');
        signInBtn.disabled = false;
        await render();
      } catch (err) {
        setStatus(err.message || 'Failed to complete sign-in.', true);
        signInBtn.disabled = false;
      }
    }
  );
}

async function signOut() {
  const client = await initSupabase();

  if (client) {
    try {
      await client.auth.signOut();
    } catch (err) {
      console.error('Sign out error:', err);
    }
  }

  await clearLocalUser();
  await render();
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

  // Save locally
  const updatedUser = { ...user, ...settings };
  await saveLocalUser(updatedUser);

  // Upsert to Supabase (best-effort — local save is primary)
  try {
    const client = await initSupabase();
    if (client) {
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

      if (error) {
        console.warn('[Reviewer] Supabase upsert skipped:', error.message);
      }
    }
  } catch (err) {
    console.warn('[Reviewer] Supabase upsert skipped:', err.message);
  }

  setSaveLoading(false);
  setStatus('');
  await render();
}

// --- Paywall ---

const API_BASE = 'https://reviewer-lovat.vercel.app';

async function openCheckout(plan) {
  const user = await getLocalUser();
  if (!user?.access_token) {
    setStatus(t('pleaseSignIn'), true);
    return;
  }

  // Ensure we have a fresh token via Supabase session refresh
  let freshToken = user.access_token;
  try {
    const client = await initSupabase();
    if (client) {
      const { data } = await client.auth.getSession();
      if (data?.session?.access_token) {
        freshToken = data.session.access_token;
      }
    }
  } catch (e) {
    console.warn('Session refresh failed:', e.message);
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
      chrome.tabs.create({ url: data.checkout_url });
      setStatus(t('checkoutOpened'));
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

// --- Events ---

signInBtn.addEventListener('click', signInWithGoogle);
signOutBtn.addEventListener('click', signOut);
setupForm.addEventListener('submit', saveSettings);
editSettingsBtn.addEventListener('click', () => {
  getLocalUser().then((user) => {
    if (!user) return;
    showSection('setup');
    hydrateSettingsForm(user);
  });
});
upgradeMonthlyBtn.addEventListener('click', () => openCheckout('monthly'));
upgradeLifetimeBtn.addEventListener('click', () => openCheckout('lifetime'));

// Initialize
applyTranslations();
render();
