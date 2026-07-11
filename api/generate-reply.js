/**
 * POST /api/generate-reply
 * Generates a human-like reply and tracks usage in Supabase.
 */

import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
const supabase = createClient(supabaseUrl, supabaseKey);

const FREE_REPLY_LIMIT = 5;

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method Not Allowed' });
  }

  try {
    // 1. استقبال البيانات من الإضافة
    const { reviewText, rating, businessName, tone, signOff, negativeStrategy, customInstructions } = req.body;

    // استخراج توكن المستخدم
    const authHeader = req.headers.authorization;
    const token = authHeader ? authHeader.replace('Bearer ', '') : null;

    if (!token) {
      return res.status(401).json({ error: 'Unauthorized: No token provided' });
    }

    // 2. التحقق من هوية المستخدم عبر Supabase
    const { data: { user }, error: userError } = await supabase.auth.getUser(token);
    if (userError || !user) {
      return res.status(401).json({ error: 'Invalid or expired token' });
    }

    // 3. جلب بيانات المستخدم
    const { data: userData, error: dbError } = await supabase
      .from('users')
      .select('replies_count, is_paid')
      .eq('id', user.id)
      .single();

    if (dbError) throw dbError;

    // 4. فحص حاجز الدفع (Paywall)
    if (!userData.is_paid && userData.replies_count >= FREE_REPLY_LIMIT) {
      return res.status(403).json({ error: 'PAYWALL' });
    }

    // 5. بناء الـ Prompt
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

    const prompt = `You are a customer service agent for ${businessName || 'Local business'}. The customer wrote: "${reviewText}" with a ${rating || 'not provided'}-star rating. Write a reply in a ${toneMap[tone] || tone || 'Friendly & Warm'} tone. CRITICAL RULES: Be human, concise, and empathetic if the review is negative. Do NOT use robotic phrases like 'We apologize' or 'Thank you for your feedback'. Speak like a real person talking to another person. Output the reply directly with no quotation marks.${rating && rating <= 2 && negativeStrategy ? ` If the review is negative, follow this strategy: ${strategyMap[negativeStrategy] || negativeStrategy}.` : ''}${signOff ? ` End with this sign-off: ${signOff}` : ''}${customInstructions ? ` Additional instructions: ${customInstructions}` : ''}`;

    // 6. استدعاء OpenRouter
    const aiResponse = await fetch('https://openrouter.ai/api/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.OPENROUTER_API_KEY}`,
      },
      body: JSON.stringify({
        model: 'google/gemma-2-9b-it:free',
        messages: [{ role: 'user', content: prompt }],
        temperature: 0.8,
      }),
    });

    const aiData = await aiResponse.json();

    // 7. التحقق من صحة الرد
    if (!aiData.choices || !aiData.choices[0]) {
      console.error('AI Error Details:', JSON.stringify(aiData));
      throw new Error('AI failed to generate a reply');
    }

    const generatedReply = aiData.choices[0].message.content.trim();

    // 8. زيادة عداد الردود للمستخدم المجاني
    if (!userData.is_paid) {
      await supabase
        .from('users')
        .update({ replies_count: userData.replies_count + 1 })
        .eq('id', user.id);
    }

    // 9. إرجاع الرد
    return res.status(200).json({ reply: generatedReply, replies_count: userData.is_paid ? userData.replies_count : userData.replies_count + 1 });

  } catch (error) {
    console.error('Server Error:', error.message);
    return res.status(500).json({ error: 'Internal Server Error' });
  }
}
