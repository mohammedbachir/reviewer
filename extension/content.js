/**
 * Reviewer — Content script for Google Maps
 * Button anchored to the REVIEW CARD, not the text.
 * Survives "Show more" expansion.
 */

const BUTTON_CLASS = 'reviewer-fast-reply-btn';
const INJECTED_ATTR = 'data-reviewer-injected';
const RESULT_CLASS = 'reviewer-reply-result';

console.log('[Reviewer] Content script loaded on:', window.location.href);

// =============================================
// Debounced triggers
// =============================================

let _timer = null;
function scheduleScan() {
  if (_timer) clearTimeout(_timer);
  _timer = setTimeout(scanAndInject, 350);
}

const observer = new MutationObserver(scheduleScan);
observer.observe(document.body, { childList: true, subtree: true });

let _scrollTimer = null;
window.addEventListener('scroll', () => {
  if (_scrollTimer) clearTimeout(_scrollTimer);
  _scrollTimer = setTimeout(scanAndInject, 500);
}, { passive: true });

setInterval(scanAndInject, 3000);
setTimeout(scanAndInject, 2000);
setTimeout(scanAndInject, 4000);

// =============================================
// Core scan
// =============================================

function scanAndInject() {
  const reviewCards = document.querySelectorAll('[data-review-id]');

  for (const card of reviewCards) {
    // CHECK 1: Flag on the CARD itself (not the text)
    if (card.getAttribute(INJECTED_ATTR) === 'true') continue;

    // CHECK 2: Button already inside this card
    if (card.querySelector(`.${BUTTON_CLASS}`)) {
      card.setAttribute(INJECTED_ATTR, 'true');
      continue;
    }

    // Extract review text for the API call
    const reviewText = extractReviewText(card);
    if (!reviewText || reviewText.length < 10) continue;

    // CHECK 3: Global fingerprint
    const fp = normalize(reviewText).substring(0, 80);
    let isDup = false;
    for (const btn of document.querySelectorAll(`.${BUTTON_CLASS}`)) {
      const stored = btn.getAttribute('data-review-text') || '';
      const storedNorm = normalize(stored);
      if (storedNorm.substring(0, 80) === fp) { isDup = true; break; }
      if (storedNorm.length > 10 && fp.length > 10) {
        if (storedNorm.includes(fp) || fp.includes(storedNorm)) { isDup = true; break; }
      }
    }
    if (isDup) {
      card.setAttribute(INJECTED_ATTR, 'true');
      continue;
    }

    // ---- ALL CLEAR — inject ----

    // Flag the CARD first
    card.setAttribute(INJECTED_ATTR, 'true');

    const rating = extractRating(card);
    const language = detectLanguage(reviewText);
    const button = createButton(reviewText, rating, language);

    // Find the action bar and insert AFTER it
    const anchor = findActionbar(card);
    anchor.appendChild(button);
  }
}

// =============================================
// Find the action bar (Like / Share / Flag row)
// and return it as the injection point.
// This survives "Show more" because the action bar
// is structural — it doesn't change when text expands.
// =============================================

function findActionbar(card) {
  // Look for the action row — it's a div containing multiple small buttons
  // (Like, Share, Flag, etc.) typically at the bottom of the review
  const allBtns = card.querySelectorAll('button, [role="button"], span[role="button"]');
  let lastActionBtn = null;

  // Arabic + English action keywords
  const keywords = [
    'like', 'share', 'flag', 'report',
    'أعجبني', 'مشاركة', 'إبلاغ', 'إبلاغ عن',
    'helpful', 'useful'
  ];

  for (const btn of allBtns) {
    const t = (btn.textContent?.trim().toLowerCase()) || '';
    // Check aria-label too (Google Maps often uses aria for these)
    const aria = (btn.getAttribute('aria-label') || '').toLowerCase();
    const combined = t + ' ' + aria;

    for (const kw of keywords) {
      if (combined.includes(kw)) {
        lastActionBtn = btn;
        break;
      }
    }
  }

  if (lastActionBtn) {
    // The action ROW is the parent div that contains this button
    const row = lastActionBtn.closest('div[class]') || lastActionBtn.parentElement;
    if (row?.parentElement) {
      const wrapper = document.createElement('div');
      wrapper.style.cssText = 'margin-top:8px;padding-top:8px;border-top:1px solid #E5E7EB;clear:both;';
      row.parentElement.insertBefore(wrapper, row.nextSibling);
      return wrapper;
    }
  }

  // Fallback: create wrapper at the very end of the card
  const wrapper = document.createElement('div');
  wrapper.style.cssText = 'margin-top:8px;padding-top:8px;border-top:1px solid #E5E7EB;clear:both;';
  card.appendChild(wrapper);
  return wrapper;
}

// =============================================
// Extract review text
// =============================================

function extractReviewText(card) {
  let longest = '';
  for (const span of card.querySelectorAll('span')) {
    const text = span.textContent?.trim() || '';
    if (
      text.length > 15 &&
      text.length > longest.length &&
      text.length < 5000 &&
      !/^\d+\s*star/i.test(text) &&
      !/^(reply|respond|like|share|more|flag|report|translated|original|view more|see more)$/i.test(text) &&
      !/^\d+ (minute|hour|day|week|month|year)s? ago$/i.test(text) &&
      !span.closest(`.${BUTTON_CLASS}`) &&
      !span.closest(`.${RESULT_CLASS}`)
    ) {
      longest = text;
    }
  }
  return longest;
}

// =============================================
// Extract rating
// =============================================

function extractRating(card) {
  for (const el of card.querySelectorAll('[aria-label]')) {
    const m = (el.getAttribute('aria-label') || '').match(/(\d)\s*star/i);
    if (m) return Number(m[1]);
  }
  return null;
}

// =============================================
// Language detection
// =============================================

function detectLanguage(text) {
  const m = text.match(/[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]/g);
  const arabic = m ? m.length : 0;
  const total = text.replace(/\s/g, '').length;
  if (total === 0) return 'en';
  return arabic / total > 0.3 ? 'ar' : 'en';
}

// =============================================
// Helpers
// =============================================

function normalize(text) {
  return text.replace(/\s+/g, ' ').trim().toLowerCase();
}

function createButton(reviewText, rating, language) {
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = BUTTON_CLASS;
  btn.textContent = t('giveAnswer');
  btn.title = t('giveAnswer');
  btn.setAttribute('data-review-text', reviewText);

  btn.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    handleClick(btn, reviewText, rating, language);
  });

  return btn;
}

async function handleClick(button, reviewText, rating, language) {
  const { user } = await chrome.storage.local.get('user');

  if (!user?.access_token) {
    showResult(button, t('signInFirst'), 'error');
    return;
  }

  if (button.disabled) return;
  button.disabled = true;
  button.textContent = t('letMeThink');

  try {
    const response = await chrome.runtime.sendMessage({
      type: 'GENERATE_REPLY',
      payload: { reviewText, rating, language },
    });

    if (!response?.ok) {
      // PAYWALL — open Paddle checkout in a new tab
      if (response?.error === 'PAYWALL') {
        const { user } = await chrome.storage.local.get('user');
        if (user?.email) {
          showResult(button, t('paywallMessage'), 'error');
          chrome.runtime.sendMessage({
            type: 'OPEN_CHECKOUT',
            payload: { email: user.email },
          });
        } else {
          showResult(button, t('signInRequired'), 'error');
        }
        return;
      }
      throw new Error(response?.error || 'Unknown error');
    }
    showResult(button, response.reply, 'success');
  } catch (error) {
    showResult(button, error.message, 'error');
  } finally {
    button.disabled = false;
    button.textContent = t('giveAnswer');
  }
}

function showResult(button, text, type) {
  const prev = button.parentElement?.querySelector(`.${RESULT_CLASS}`);
  if (prev) prev.remove();

  const result = document.createElement('div');
  result.className = RESULT_CLASS;
  result.textContent = text;

  if (type === 'error') {
    result.style.color = '#DC2626';
  } else {
    result.style.color = '#374151';
    const copyBtn = document.createElement('button');
    copyBtn.textContent = t('copy');
    copyBtn.className = 'reviewer-copy-btn';
    copyBtn.addEventListener('click', () => {
      navigator.clipboard.writeText(text).then(() => {
        copyBtn.textContent = t('copied');
        setTimeout(() => { copyBtn.textContent = t('copy'); }, 2000);
      });
    });
    result.appendChild(copyBtn);
  }

  button.after(result);
}
