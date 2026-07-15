/**
 * POST /api/generate-reply
 * Multi-agent system: generates 3 replies in parallel, scores them,
 * and returns the most human-like one.
 */

import { createClient } from '@supabase/supabase-js';
import { scoreReply } from './score-reply.js';

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
const supabase = createClient(supabaseUrl, supabaseKey);

const FREE_REPLY_LIMIT = 5;

// ─── Clean AI artifacts ─────────────────────────────────────────────────────

function cleanReply(text) {
  if (!text) return text;

  let result = text.trim();

  // Remove wrapping quotes
  result = result.replace(/^["'""]|["'""]$/g, '');

  // Remove anything after "Reply:" or "Reply in" if it's the AI explaining
  result = result.replace(/\n\s*(Reply|Answer|Response|Output|Here)[:\s].*$/is, '');

  // Remove lines that look like AI reasoning/explanations
  result = result.split('\n').filter(line => {
    const trimmed = line.trim();
    // Skip lines that are clearly not replies
    if (/^(RULES|NOTE|IMPORTANT|STEP|BREAKDOWN|SCORE|ANALYSIS|REASONING|EXPLANATION|CONTEXT|INSTRUCTION)/i.test(trimmed)) return false;
    if (/^(I need to|I should|Let me|First|Second|Third|Finally|In conclusion)/i.test(trimmed)) return false;
    if (/^(The review|The customer|This review|The rating)/i.test(trimmed)) return false;
    return true;
  }).join('\n');

  // Remove trailing gibberish
  result = result.replace(/([.!?؟！])([^.!?؟！\n]{0,30})$/s, (match, punct, tail) => {
    if (tail.trim().length < 5 || /^[^\s]{3,}$/.test(tail.trim())) {
      return punct;
    }
    return match;
  });

  // If result is way too long, truncate at last sentence under 300 chars
  if (result.length > 300) {
    const sentences = result.match(/[^.!?؟!]+[.!?؟!]+/g) || [result];
    let truncated = '';
    for (const s of sentences) {
      if ((truncated + s).length > 280) break;
      truncated += s;
    }
    result = truncated || result.substring(0, 280);
  }

  return result.trim();
}

// ─── Agent Prompts ──────────────────────────────────────────────────────────

const AGENT_PROMPTS = {
  friendly: (ctx) => `Reply to this customer review as a friendly, warm business owner for ${ctx.businessName}.

Review: "${ctx.reviewText}" (${ctx.rating} stars)

RULES:
- 1-3 sentences ONLY
- Be genuine, warm, natural
- NO robotic phrases like "Thank you for your feedback"
- NO explanations, NO reasoning, just the reply text
- ${ctx.replyLang} language only
${ctx.strategyAdvice ? `- ${ctx.strategyAdvice}` : ''}
${ctx.signOff ? `- End with: ${ctx.signOff}` : ''}
${ctx.customInstructions ? `- ${ctx.customInstructions}` : ''}

Write ONLY the reply text, nothing else:`,

  professional: (ctx) => `Reply to this customer review as a professional business representative for ${ctx.businessName}.

Review: "${ctx.reviewText}" (${ctx.rating} stars)

RULES:
- 1-3 sentences ONLY
- Polished but human, NOT corporate
- NO phrases like "Thank you for your feedback" or "We value your business"
- NO explanations, NO reasoning, just the reply text
- ${ctx.replyLang} language only
${ctx.strategyAdvice ? `- ${ctx.strategyAdvice}` : ''}
${ctx.signOff ? `- End with: ${ctx.signOff}` : ''}
${ctx.customInstructions ? `- ${ctx.customInstructions}` : ''}

Write ONLY the reply text, nothing else:`,

  casual: (ctx) => `Reply to this customer review as a casual, laid-back business owner for ${ctx.businessName}.

Review: "${ctx.reviewText}" (${ctx.rating} stars)

RULES:
- 1-3 sentences ONLY
- Use contractions, be relaxed, sound like a real person
- NO formal AI phrases
- NO explanations, NO reasoning, just the reply text
- ${ctx.replyLang} language only
${ctx.strategyAdvice ? `- ${ctx.strategyAdvice}` : ''}
${ctx.signOff ? `- End with: ${ctx.signOff}` : ''}
${ctx.customInstructions ? `- ${ctx.customInstructions}` : ''}

Write ONLY the reply text, nothing else:`,
};

// ─── Generate one reply from one agent ──────────────────────────────────────

async function generateAgentReply(agentName, prompt) {
  try {
    const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.OPENROUTER_API_KEY}`,
      },
      body: JSON.stringify({
        model: 'openrouter/free',
        messages: [{ role: 'user', content: prompt }],
        temperature: 0.85,
        max_tokens: 150,
      }),
    });

    const data = await response.json();

    if (!data.choices || !data.choices[0]) {
      console.error(`[Agent ${agentName}] Error:`, JSON.stringify(data));
      return null;
    }

    const reply = cleanReply(data.choices[0].message.content.trim());
    return reply;
  } catch (err) {
    console.error(`[Agent ${agentName}] Failed:`, err.message);
    return null;
  }
}

// ─── Main Handler ───────────────────────────────────────────────────────────

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

    // Fetch user settings
    let userData = { replies_count: 0, is_paid: false, business_name: '', sign_off: '', tone: 'friendly', negative_strategy: 'apologize', custom_instructions: '' };

    const { data: dbUser } = await supabase
      .from('users')
      .select('*')
      .eq('id', user.id)
      .single();

    if (dbUser) {
      userData = { ...userData, ...dbUser };
    } else {
      await supabase.from('users').upsert({
        id: user.id,
        email: user.email,
        replies_count: 0,
        is_paid: false,
      }, { onConflict: 'id' });
    }

    // PAYWALL DISABLED
    // if (!userData.is_paid && userData.replies_count >= FREE_REPLY_LIMIT) {
    //   return res.status(403).json({ error: 'PAYWALL' });
    // }

    const strategyMap = {
      apologize: 'If the review is negative, apologize sincerely.',
      email: 'If the review is negative, ask them to contact via email.',
      discount: 'If the review is negative, offer a 10% discount.',
    };

    const replyLang = language === 'ar' ? 'Arabic' : 'English';

    const ctx = {
      businessName: userData.business_name || 'Local business',
      reviewText,
      rating: rating || 'not provided',
      replyLang,
      strategyAdvice: rating && rating <= 2 && userData.negative_strategy
        ? strategyMap[userData.negative_strategy] || ''
        : '',
      signOff: userData.sign_off || '',
      customInstructions: userData.custom_instructions || '',
    };

    // ─── Generate 3 replies in parallel ─────────────────────────────────────

    console.log('[MultiAgent] Generating 3 replies in parallel...');

    const [replyA, replyB, replyC] = await Promise.all([
      generateAgentReply('friendly', AGENT_PROMPTS.friendly(ctx)),
      generateAgentReply('professional', AGENT_PROMPTS.professional(ctx)),
      generateAgentReply('casual', AGENT_PROMPTS.casual(ctx)),
    ]);

    const candidates = [
      { agent: 'friendly', reply: replyA },
      { agent: 'professional', reply: replyB },
      { agent: 'casual', reply: replyC },
    ].filter(c => c.reply && c.reply.length > 5);

    if (candidates.length === 0) {
      throw new Error('All agents failed to generate a reply');
    }

    // ─── Score each reply ───────────────────────────────────────────────────

    console.log('[MultiAgent] Scoring', candidates.length, 'candidates...');

    const scored = candidates.map(c => {
      const { scores, total } = scoreReply(c.reply, reviewText, rating);
      return {
        agent: c.agent,
        reply: c.reply,
        score: total,
        breakdown: scores,
      };
    });

    // Sort by score descending
    scored.sort((a, b) => b.score - a.score);

    const best = scored[0];

    console.log('[MultiAgent] Best agent:', best.agent, '| Score:', best.score);
    console.log('[MultiAgent] All scores:', scored.map(s => `${s.agent}: ${s.score}`).join(' | '));

    // Update reply count
    if (!userData.is_paid) {
      const newCount = userData.replies_count + 1;
      await supabase
        .from('users')
        .update({ replies_count: newCount })
        .eq('id', user.id);
      return res.status(200).json({
        reply: best.reply,
        replies_count: newCount,
        agent: best.agent,
        score: best.score,
        allScores: scored.map(s => ({ agent: s.agent, score: s.score })),
      });
    }

    return res.status(200).json({
      reply: best.reply,
      replies_count: userData.replies_count,
      agent: best.agent,
      score: best.score,
      allScores: scored.map(s => ({ agent: s.agent, score: s.score })),
    });

  } catch (error) {
    console.error('Server Error:', error.message, error.stack);
    return res.status(500).json({ error: error.message || 'Internal Server Error' });
  }
}
