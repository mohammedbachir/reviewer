/**
 * POST /api/generate-reply
 * Generates a human-like reply and tracks usage in Supabase.
 */

import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
const supabase = createClient(supabaseUrl, supabaseKey);

const FREE_REPLY_LIMIT = 5;

function cleanReply(text) {
  if (!text) return text;

  // Remove trailing lines that look like random gibberish
  // (short strings with high consonant ratio, no real words)
  const lines = text.split('\n').filter(line => {
    const trimmed = line.trim();
    if (!trimmed) return true; // keep empty lines
    // If line is short (< 8 chars) and has mostly consonants, skip it
    if (trimmed.length < 8 && /^[bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ\s]{3,}$/.test(trimmed)) {
      return false;
    }
    return true;
  });

  let result = lines.join('\n').trim();

  // Remove trailing gibberish after last punctuation (period, exclamation, question mark)
  // e.g. "Great review! trhrth" → "Great review!"
  result = result.replace(/([.!?؟！])([^.!?؟！\n]{0,30})$/s, (match, punct, tail) => {
    // If tail has no spaces or is very short and looks random, drop it
    if (tail.trim().length < 5 || /^[^\s]{3,}$/.test(tail.trim())) {
      return punct;
    }
    return match;
  });

  return result.trim();
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method Not Allowed' });
  }

  try {
    const { reviewText, rating, language } = req.body;

    if (!reviewText || reviewText.length < 5) {
      return res.status(400).json({ error: 'Review text is required.' });
    }

    const authHeader = req.headers.authorization;
    const token = authHeader ? authHeader.replace('Bearer ', '') : null;

    if (!token) {
      return res.status(401).json({ error: 'Unauthorized: No token provided' });
    }

    const { data: { user }, error: userError } = await supabase.auth.getUser(token);
    if (userError || !user) {
      return res.status(401).json({ error: 'Invalid or expired token' });
    }

    // Fetch user settings + usage from DB (with fallback defaults)
    let userData = { replies_count: 0, is_paid: false, business_name: '', sign_off: '', tone: 'friendly', negative_strategy: 'apologize', custom_instructions: '' };

    const { data: dbUser } = await supabase
      .from('users')
      .select('*')
      .eq('id', user.id)
      .single();

    if (dbUser) {
      userData = { ...userData, ...dbUser };
    } else {
      // First time: create user record
      await supabase.from('users').upsert({
        id: user.id,
        email: user.email,
        replies_count: 0,
        is_paid: false,
      }, { onConflict: 'id' });
    }

    // PAYWALL DISABLED — app is free for now
    // if (!userData.is_paid && userData.replies_count >= FREE_REPLY_LIMIT) {
    //   return res.status(403).json({ error: 'PAYWALL' });
    // }

    const toneMap = {
      friendly: 'Friendly & Warm',
      professional: 'Professional & Formal',
      casual: 'Casual & Witty',
      human: 'Real & Natural',
    };

    const strategyMap = {
      apologize: 'Just apologize sincerely',
      email: 'Ask them to contact us via email',
      discount: 'Offer a 10% discount on their next visit',
    };

    const replyLang = language === 'ar' ? 'Arabic' : 'English';
    const prompt = `You are a customer service agent for ${userData.business_name || 'Local business'}. The customer wrote: "${reviewText}" with a ${rating || 'not provided'}-star rating. Write a reply in ${replyLang} language in a ${toneMap[userData.tone] || 'Friendly & Warm'} tone. CRITICAL RULES: Be human, concise, and empathetic if the review is negative. Do NOT use robotic phrases like 'We apologize' or 'Thank you for your feedback'. Speak like a real person talking to another person. Output the reply directly with no quotation marks.${rating && rating <= 2 && userData.negative_strategy ? ` If the review is negative, follow this strategy: ${strategyMap[userData.negative_strategy] || userData.negative_strategy}.` : ''}${userData.sign_off ? ` End with this sign-off: ${userData.sign_off}` : ''}${userData.custom_instructions ? ` Additional instructions: ${userData.custom_instructions}` : ''}`;

    const aiResponse = await fetch('https://openrouter.ai/api/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.OPENROUTER_API_KEY}`,
      },
      body: JSON.stringify({
        model: 'openrouter/free',
        messages: [{ role: 'user', content: prompt }],
        temperature: 0.8,
      }),
    });

    const aiData = await aiResponse.json();

    if (!aiData.choices || !aiData.choices[0]) {
      console.error('AI Error Details:', JSON.stringify(aiData));
      throw new Error(aiData.error?.message || 'AI failed to generate a reply');
    }

    let generatedReply = aiData.choices[0].message.content.trim();

    // Clean up AI artifacts: remove trailing gibberish (random chars, repeated letters, etc.)
    generatedReply = cleanReply(generatedReply);

    if (!userData.is_paid) {
      const newCount = userData.replies_count + 1;
      await supabase
        .from('users')
        .update({ replies_count: newCount })
        .eq('id', user.id);
      return res.status(200).json({ reply: generatedReply, replies_count: newCount });
    }

    return res.status(200).json({ reply: generatedReply, replies_count: userData.replies_count });

  } catch (error) {
    console.error('Server Error:', error.message, error.stack);
    return res.status(500).json({ error: error.message || 'Internal Server Error' });
  }
}
