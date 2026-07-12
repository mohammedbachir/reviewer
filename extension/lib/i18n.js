/**
 * Reviewer — i18n
 * Detects browser language and provides translations for Arabic (ar) and English (en).
 */

const TRANSLATIONS = {
  ar: {
    // Content script
    giveAnswer: 'Give it Answer',
    letMeThink: 'I\'m thinking...',
    copy: 'Copy',
    copied: 'Copied!',
    signInFirst: 'Please sign in from the extension popup first.',
    paywallMessage: 'You\'ve used all 5 free replies. Upgrade to Reply Pro for unlimited smart responses to all your Google reviews.',
    signInRequired: 'Please sign in from the extension popup.',

    // Popup — Auth
    appTitle: 'Reviewer',
    appSubtext: 'Reply to Google reviews in seconds with smart responses that sound like you.',
    signInGoogle: 'Sign in with Google',
    trustNote: 'Your data stays private. We only access your review settings.',

    // Popup — Setup
    stepLabel: 'Step 1 of 1',
    businessProfile: 'Business Profile',
    businessName: 'Business Name',
    businessNamePlaceholder: 'e.g. Cafe Morning',
    signOff: 'Sign-off',
    signOffPlaceholder: 'e.g. Best, The Cafe Team',
    signOffHint: 'How should replies end?',
    replyTone: 'Reply Tone',
    toneFriendly: 'Friendly & Warm',
    toneProfessional: 'Professional & Formal',
    toneCasual: 'Casual & Witty',
    toneHuman: 'Real & Natural',
    negativeStrategy: 'Negative Review Strategy',
    strategyApologize: 'Just apologize',
    strategyEmail: 'Ask them to email us',
    strategyDiscount: 'Offer a 10% discount',
    negativeHint: 'What to do if rating is 1 or 2 stars?',
    customInstructions: 'Custom Instructions',
    customPlaceholder: 'e.g. Never mention competitors. We are closed on Sundays.',
    customHint: 'Any specific rules the replies should follow?',
    saveContinue: 'Save & Continue',

    // Popup — Ready
    allSet: 'You\'re all set',
    readyText: 'Go to your Google Business Reviews and click the Give it Answer button.',
    planPro: 'Plan: Pro — unlimited replies',
    freeRepliesLeft: (n) => `You have ${n} free ${n === 1 ? 'reply' : 'replies'} left.`,
    editSettings: 'Edit settings',

    // Popup — Paywall
    upgradeTitle: 'Upgrade to Reply Pro',
    upgradeSubtext: 'You\'ve used all 5 free replies. Unlock the full power of Reviewer.',
    featureUnlimited: 'Unlimited smart replies to all reviews',
    featureTone: 'Matches your brand tone and style',
    featureLanguages: 'Auto-replies in any language',
    featureNegative: 'Negative review handling strategies',
    monthly: 'Monthly',
    lifetime: 'Lifetime',
    bestValue: 'Best value',
    perMonth: '/mo',
    once: 'once',

    // Popup — Status
    openingCheckout: (plan) => `Opening ${plan} checkout...`,
    checkoutOpened: 'Checkout opened in a new tab. Complete your payment there.',
    pleaseSignIn: 'Please sign in first.',

    // Footer
    signOut: 'Sign out',

    // Errors
    enterBusinessName: 'Please enter your business name.',
    sessionExpired: 'Session expired. Please sign in again from the popup.',
  },

  en: {
    // Content script
    giveAnswer: 'Give it Answer',
    letMeThink: 'Let me think...',
    copy: 'Copy',
    copied: 'Copied!',
    signInFirst: 'Please sign in from the extension popup first.',
    paywallMessage: 'You\'ve used all 5 free replies. Upgrade to Reply Pro for unlimited smart responses to all your Google reviews.',
    signInRequired: 'Please sign in from the extension popup.',

    // Popup — Auth
    appTitle: 'Reviewer',
    appSubtext: 'Reply to Google reviews in seconds with smart responses that sound like you.',
    signInGoogle: 'Sign in with Google',
    trustNote: 'Your data stays private. We only access your review settings.',

    // Popup — Setup
    stepLabel: 'Step 1 of 1',
    businessProfile: 'Business Profile',
    businessName: 'Business Name',
    businessNamePlaceholder: 'e.g. Cafe Morning',
    signOff: 'Sign-off',
    signOffPlaceholder: 'e.g. Best, The Cafe Team',
    signOffHint: 'How should replies end?',
    replyTone: 'Reply Tone',
    toneFriendly: 'Friendly & Warm',
    toneProfessional: 'Professional & Formal',
    toneCasual: 'Casual & Witty',
    toneHuman: 'Real & Natural',
    negativeStrategy: 'Negative Review Strategy',
    strategyApologize: 'Just apologize',
    strategyEmail: 'Ask them to email us',
    strategyDiscount: 'Offer a 10% discount',
    negativeHint: 'What to do if rating is 1 or 2 stars?',
    customInstructions: 'Custom Instructions',
    customPlaceholder: 'e.g. Never mention competitors. We are closed on Sundays.',
    customHint: 'Any specific rules the replies should follow?',
    saveContinue: 'Save & Continue',

    // Popup — Ready
    allSet: 'You\'re all set',
    readyText: 'Go to your Google Business Reviews and click the Give it Answer button.',
    planPro: 'Plan: Pro — unlimited replies',
    freeRepliesLeft: (n) => `You have ${n} free ${n === 1 ? 'reply' : 'replies'} left.`,
    editSettings: 'Edit settings',

    // Popup — Paywall
    upgradeTitle: 'Upgrade to Reply Pro',
    upgradeSubtext: 'You\'ve used all 5 free replies. Unlock the full power of Reviewer.',
    featureUnlimited: 'Unlimited smart replies to all reviews',
    featureTone: 'Matches your brand tone and style',
    featureLanguages: 'Auto-replies in any language',
    featureNegative: 'Negative review handling strategies',
    monthly: 'Monthly',
    lifetime: 'Lifetime',
    bestValue: 'Best value',
    perMonth: '/mo',
    once: 'once',

    // Popup — Status
    openingCheckout: (plan) => `Opening ${plan} checkout...`,
    checkoutOpened: 'Checkout opened in a new tab. Complete your payment there.',
    pleaseSignIn: 'Please sign in first.',

    // Footer
    signOut: 'Sign out',

    // Errors
    enterBusinessName: 'Please enter your business name.',
    sessionExpired: 'Session expired. Please sign in again from the popup.',
  },
};

function detectLanguage() {
  const lang = (navigator.language || navigator.userLanguage || 'en').toLowerCase();
  return lang.startsWith('ar') ? 'ar' : 'en';
}

function t(key) {
  const lang = detectLanguage();
  const val = TRANSLATIONS[lang]?.[key] ?? TRANSLATIONS.en[key] ?? key;
  return typeof val === 'function' ? val : val;
}

function setDir() {
  document.documentElement.dir = detectLanguage() === 'ar' ? 'rtl' : 'ltr';
  document.documentElement.lang = detectLanguage();
}

// Auto-set direction on load
if (typeof document !== 'undefined') {
  setDir();
}
