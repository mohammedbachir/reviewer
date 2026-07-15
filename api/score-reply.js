/**
 * Human-Like Reply Scoring Algorithm
 * Scores a reply on how human-like it sounds (0-100).
 */

// Common AI phrases that sound robotic
const AI_PHRASES = [
  'thank you for your feedback',
  'thank you for your review',
  'we appreciate your feedback',
  'we appreciate your review',
  'we look forward to serving you',
  'we value your business',
  'your satisfaction is our priority',
  'we are committed to',
  'we strive to',
  'please do not hesitate to contact us',
  'feel free to reach out',
  'we apologize for any inconvenience',
  'we sincerely apologize',
  'your feedback is important to us',
  'we are always happy to help',
  'we hope to see you again',
  'welcome back anytime',
  'thank you for choosing us',
  'we appreciate your patronage',
  'best regards',
  'kind regards',
  'sincerely',
];

/**
 * 1. Sentence Variation (0-100)
 * Humans write sentences of varying lengths. AI tends to write uniform sentences.
 */
function sentenceVariation(text) {
  const sentences = text.split(/[.!?؟!]+/).filter(s => s.trim().length > 0);
  if (sentences.length < 2) return 50; // Neutral for single sentence

  const lengths = sentences.map(s => s.trim().split(/\s+/).length);
  const avg = lengths.reduce((a, b) => a + b, 0) / lengths.length;
  const variance = lengths.reduce((sum, l) => sum + Math.pow(l - avg, 2), 0) / lengths.length;
  const stdDev = Math.sqrt(variance);

  // Good variation: stdDev > 3. Low variation: stdDev < 1
  const score = Math.min(100, stdDev * 20);
  return Math.max(0, score);
}

/**
 * 2. Word Diversity (0-100)
 * Humans use varied vocabulary. AI repeats words.
 */
function wordDiversity(text) {
  const words = text.toLowerCase().replace(/[^a-zA-Z\u0600-\u06FF\s]/g, '').split(/\s+/).filter(w => w.length > 2);
  if (words.length < 5) return 50;

  const unique = new Set(words);
  const ratio = unique.size / words.length;

  // ratio > 0.7 = great diversity, < 0.4 = repetitive
  return Math.min(100, ratio * 120);
}

/**
 * 3. Punctuation Variety (0-100)
 * Humans use varied punctuation. AI uses periods mostly.
 */
function punctuationVariety(text) {
  const punctuation = text.match(/[.!?,;:!?؟！，。、；：]/g) || [];
  if (punctuation.length === 0) return 60; // No punctuation is okay sometimes

  const types = new Set(punctuation);
  const variety = types.size;

  // Also check for emojis (human touch)
  const emojiCount = (text.match(/[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu) || []).length;

  const score = Math.min(100, (variety * 20) + (emojiCount * 10));
  return score;
}

/**
 * 4. Personal Touch (0-100)
 * Does the reply reference specific details from the review?
 */
function personalTouch(replyText, reviewText) {
  const reviewWords = reviewText.toLowerCase().replace(/[^a-zA-Z\u0600-\u06FF\s]/g, '').split(/\s+/).filter(w => w.length > 4);
  const replyLower = replyText.toLowerCase();

  if (reviewWords.length === 0) return 50;

  let matches = 0;
  for (const word of reviewWords) {
    if (replyLower.includes(word)) {
      matches++;
    }
  }

  // Also check for partial matches (word stems)
  let partialMatches = 0;
  for (const word of reviewWords) {
    const stem = word.slice(0, Math.max(4, word.length - 2));
    if (replyLower.includes(stem)) {
      partialMatches++;
    }
  }

  const totalScore = (matches * 15) + (partialMatches * 5);
  return Math.min(100, totalScore);
}

/**
 * 5. Natural Imperfections (0-100)
 * Humans write with slight imperfections. AI is too perfect.
 */
function naturalImperfections(text) {
  let score = 50; // Base score

  // Humans sometimes use contractions
  const contractions = ["don't", "can't", "won't", "isn't", "it's", "you're", "we're", "that's", "what's", "i'm"];
  for (const c of contractions) {
    if (text.toLowerCase().includes(c)) score += 5;
  }

  // Humans sometimes start with "So" or "Oh" or "Yeah"
  const starters = /^(so|oh|yeah|hey|wow|ah|um|hmm)/i;
  if (starters.test(text.trim())) score += 8;

  // Humans sometimes use "..." (ellipsis)
  if (text.includes('...')) score += 5;

  // Humans sometimes use dashes
  if (text.includes(' — ') || text.includes(' - ')) score += 3;

  // Negative: too many exclamation marks in a row (AI habit)
  if (/!{2,}/.test(text)) score -= 5;

  // Negative: perfectly balanced sentences (AI habit)
  const sentences = text.split(/[.!?]+/).filter(s => s.trim());
  if (sentences.length >= 2) {
    const lengths = sentences.map(s => s.trim().split(/\s+/).length);
    const maxLen = Math.max(...lengths);
    const minLen = Math.min(...lengths);
    if (maxLen - minLen > 2) score += 10; // Good variation
    if (maxLen - minLen < 1) score -= 10; // Too uniform
  }

  return Math.max(0, Math.min(100, score));
}

/**
 * 6. Anti-AI Phrases (0-100)
 * Detect and penalize common AI phrases.
 */
function antiAIPhrases(text) {
  const lower = text.toLowerCase();
  let score = 100;

  for (const phrase of AI_PHRASES) {
    if (lower.includes(phrase)) {
      score -= 15;
    }
  }

  // Penalize generic openers
  if (/^(dear|to whom|hello valued)/i.test(lower.trim())) score -= 20;

  // Penalize generic closers
  if (/(sincerely|best regards|kind regards|warm regards)/i.test(lower)) score -= 15;

  // Bonus for natural openers
  if (/^(thanks|thank you|hey|hi|glad|happy|love|appreciate)/i.test(lower.trim())) score += 10;

  return Math.max(0, Math.min(100, score));
}

/**
 * 7. Tone Match (0-100)
 * Does the reply match the review's tone?
 */
function toneMatch(reviewText, rating, replyText) {
  const replyLower = replyText.toLowerCase();
  let score = 70; // Base

  if (rating && rating <= 2) {
    // Negative review: reply should be empathetic/apologetic
    const empathyWords = ['sorry', 'apologize', 'understand', 'frustrating', 'disappointing', 'improve', 'better', 'listen', 'hear', 'concern'];
    const hasEmpathy = empathyWords.some(w => replyLower.includes(w));
    if (hasEmpathy) score += 20;

    // Should NOT be overly positive
    const overlyPositive = ['amazing', 'wonderful', 'fantastic', 'love', 'great'];
    const positiveCount = overlyPositive.filter(w => replyLower.includes(w)).length;
    if (positiveCount > 1) score -= 15;
  }

  if (rating && rating >= 4) {
    // Positive review: reply should be warm and appreciative
    const warmWords = ['thank', 'glad', 'happy', 'appreciate', 'love', 'enjoy', 'thrilled', 'wonderful'];
    const hasWarmth = warmWords.some(w => replyLower.includes(w));
    if (hasWarmth) score += 15;

    // Should NOT be overly apologetic
    const apologetic = ['sorry', 'apologize', 'regret', 'unfortunately'];
    const hasApology = apologetic.some(w => replyLower.includes(w));
    if (hasApology) score -= 15;
  }

  return Math.max(0, Math.min(100, score));
}

/**
 * Main scoring function
 * @param {string} replyText - The generated reply
 * @param {string} reviewText - The original review
 * @param {number} rating - Star rating (1-5)
 * @returns {object} Score breakdown and total
 */
export function scoreReply(replyText, reviewText, rating) {
  const scores = {
    sentenceVariation: sentenceVariation(replyText),
    wordDiversity: wordDiversity(replyText),
    punctuationVariety: punctuationVariety(replyText),
    personalTouch: personalTouch(replyText, reviewText),
    naturalImperfections: naturalImperfections(replyText),
    antiAIPhrases: antiAIPhrases(replyText),
    toneMatch: toneMatch(reviewText, rating, replyText),
  };

  const weights = {
    sentenceVariation: 0.15,
    wordDiversity: 0.10,
    punctuationVariety: 0.10,
    personalTouch: 0.20,
    naturalImperfections: 0.10,
    antiAIPhrases: 0.20,
    toneMatch: 0.15,
  };

  let total = 0;
  for (const [key, weight] of Object.entries(weights)) {
    total += scores[key] * weight;
  }

  return {
    scores,
    total: Math.round(total * 10) / 10,
  };
}
