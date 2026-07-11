/**
 * Reviewer — Content script
 * Runs on business.google.com/reviews/*
 * Injects "Smart Reply ✨" buttons next to reviews.
 */

const BUTTON_CLASS = 'reviewer-smart-reply-btn';
const PROCESSED_ATTR = 'data-reviewer-processed';

// Observe DOM changes — Google Business UI is dynamic.
const observer = new MutationObserver(() => {
  scanAndInjectButtons();
});

observer.observe(document.body, { childList: true, subtree: true });

// Initial scan after page load.
scanAndInjectButtons();

/**
 * Find review blocks and inject a button into each unprocessed block.
 * Uses resilient selectors (text + structure) instead of brittle class names.
 */
function scanAndInjectButtons() {
  const reviewBlocks = findReviewBlocks();

  reviewBlocks.forEach((block) => {
    if (block.getAttribute(PROCESSED_ATTR) === 'true') return;

    const button = createSmartReplyButton();
    const anchor = findButtonAnchor(block);

    if (!anchor) return;

    anchor.appendChild(button);
    block.setAttribute(PROCESSED_ATTR, 'true');
  });
}

/**
 * Heuristic: locate elements that look like individual reviews.
 * TODO: Refine selectors after testing on live Google Business page.
 */
function findReviewBlocks() {
  const candidates = [];

  // Reviews often contain a reply action or star rating nearby.
  const replyTriggers = document.querySelectorAll('button, a, span');

  replyTriggers.forEach((el) => {
    const text = el.textContent?.trim().toLowerCase() ?? '';
    if (text === 'reply' || text === 'respond') {
      const block = el.closest('div[role="listitem"], article, li, div');
      if (block) candidates.push(block);
    }
  });

  return [...new Set(candidates)];
}

/**
 * Pick a stable place to attach our button (near the native Reply control).
 */
function findButtonAnchor(block) {
  const replyEl = [...block.querySelectorAll('button, a, span')].find((el) => {
    const text = el.textContent?.trim().toLowerCase() ?? '';
    return text === 'reply' || text === 'respond';
  });

  return replyEl?.parentElement ?? block;
}

function createSmartReplyButton() {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = BUTTON_CLASS;
  button.textContent = 'Smart Reply ✨';
  button.addEventListener('click', onSmartReplyClick);
  return button;
}

async function onSmartReplyClick(event) {
  const button = event.currentTarget;
  const block = button.closest(`[${PROCESSED_ATTR}="true"]`);

  if (!block) return;

  const reviewText = extractReviewText(block);
  const rating = extractRating(block);

  if (!reviewText) {
    alert('Could not read review text. Try refreshing the page.');
    return;
  }

  button.disabled = true;
  button.textContent = 'Generating...';

  try {
    const response = await chrome.runtime.sendMessage({
      type: 'GENERATE_REPLY',
      payload: { reviewText, rating },
    });

    if (!response?.ok) {
      throw new Error(response?.error ?? 'Unknown error');
    }

    pasteReplyIntoBox(block, response.reply);
    button.textContent = 'Smart Reply ✨';
  } catch (error) {
    alert(error.message);
    button.textContent = 'Smart Reply ✨';
  } finally {
    button.disabled = false;
  }
}

/**
 * Extract review body text from the nearest review block.
 */
function extractReviewText(block) {
  // Prefer longer text nodes; skip button labels.
  const textNodes = [...block.querySelectorAll('p, span, div')]
    .map((el) => el.textContent?.trim() ?? '')
    .filter((text) => text.length > 20 && !/^(reply|respond)$/i.test(text));

  return textNodes.sort((a, b) => b.length - a.length)[0] ?? '';
}

/**
 * Extract star rating if present (1–5).
 */
function extractRating(block) {
  const ariaLabel = block.querySelector('[aria-label*="star"]')?.getAttribute('aria-label') ?? '';
  const match = ariaLabel.match(/(\d)/);
  return match ? Number(match[1]) : null;
}

/**
 * Paste generated reply into Google's reply textarea.
 */
function pasteReplyIntoBox(block, reply) {
  const textarea =
    block.querySelector('textarea') ??
    document.querySelector('textarea[aria-label*="reply"], textarea');

  if (!textarea) {
    alert('Reply box not found. Click "Reply" first, then try again.');
    return;
  }

  textarea.focus();
  textarea.value = reply;
  textarea.dispatchEvent(new Event('input', { bubbles: true }));
}
