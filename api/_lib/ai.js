/**
 * OpenRouter provider abstraction.
 * Uses google/gemma-2-9b-it:free for human-like replies.
 */

const OPENROUTER_MODEL = 'google/gemma-2-9b-it:free';
const OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions';

const TONE_MAP = {
  friendly: 'Friendly & Warm',
  professional: 'Professional & Formal',
  casual: 'Casual & Witty',
  human: 'Real & Natural',
};

const STRATEGY_MAP = {
  apologize: 'Just apologize sincerely',
  email: 'Ask them to contact us via email',
  discount: 'Offer a 10% discount on their next visit',
};

export async function generateReply({ reviewText, rating, businessName, tone, signOff, negativeStrategy, customInstructions }) {
  const apiKey = process.env.OPENROUTER_API_KEY;
  if (!apiKey) throw new Error('Missing OPENROUTER_API_KEY.');

  const prompt = buildPrompt({ reviewText, rating, businessName, tone, signOff, negativeStrategy, customInstructions });

  const response = await fetch(OPENROUTER_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: OPENROUTER_MODEL,
      messages: [{ role: 'user', content: prompt }],
      temperature: 0.8,
    }),
  });

  const data = await response.json();

  if (!data.choices || !data.choices[0]) {
    console.error('OpenRouter Error:', JSON.stringify(data));
    throw new Error('AI failed to generate a reply.');
  }

  return data.choices[0].message.content.trim();
}

function buildPrompt({ reviewText, rating, businessName, tone, signOff, negativeStrategy, customInstructions }) {
  const toneLabel = TONE_MAP[tone] || tone || 'Friendly & Warm';
  const strategyLabel = STRATEGY_MAP[negativeStrategy] || negativeStrategy || '';

  const parts = [
    `You are a customer service agent for ${businessName || 'Local business'}.`,
    `The customer wrote: "${reviewText}" with a ${rating || 'not provided'}-star rating.`,
    `Write a reply in a ${toneLabel} tone.`,
    `CRITICAL RULES: Be human, concise, and empathetic if the review is negative.`,
    `Do NOT use robotic phrases like 'We apologize' or 'Thank you for your feedback'.`,
    `Speak like a real person talking to another person.`,
    `Output the reply directly with no quotation marks.`,
  ];

  if (rating && rating <= 2 && strategyLabel) {
    parts.push(`If the review is negative, follow this strategy: ${strategyLabel}.`);
  }

  if (signOff) {
    parts.push(`End with this sign-off: ${signOff}`);
  }

  if (customInstructions) {
    parts.push(`Additional instructions: ${customInstructions}`);
  }

  return parts.join(' ');
}
