// MCTV self-serve agreement intake (public rate calculator v2.0)
// Writes: contract_requests (truth) + quote_submissions (legacy inbox, best-effort)
// + leads + pipeline_opportunities (advertiser/contract_sent) + tasks (Creed) + activity_log.
import { createClient } from 'npm:@supabase/supabase-js@2';

const cors = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS'
};
const json = (obj: unknown, status = 200) =>
  new Response(JSON.stringify(obj), { status, headers: { ...cors, 'Content-Type': 'application/json' } });

const str = (v: unknown, max: number) => (typeof v === 'string' ? v.trim().slice(0, max) : '');
const pad = (n: number) => String(n).padStart(2, '0');

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: cors });
  if (req.method !== 'POST') return json({ error: 'method not allowed' }, 405);
  try {
    const raw = await req.text();
    if (raw.length > 60000) return json({ error: 'payload too large' }, 413);
    const b = JSON.parse(raw);

    // Honeypot: report success, write nothing
    if (typeof b.company_website === 'string' && b.company_website.trim() !== '') {
      return json({ ok: true, ref: 'SSA-RECEIVED' });
    }

    const business_name = str(b.business_name, 200);
    const contact_name = str(b.contact_name, 200);
    const contact_email = str(b.contact_email, 254).toLowerCase();
    const contact_phone = str(b.contact_phone, 60) || null;
    const signed_name = str(b.signed_name, 200);
    if (!business_name || !contact_name || !signed_name) return json({ error: 'missing required fields' }, 400);
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(contact_email)) return json({ error: 'invalid email' }, 400);
    if (b.authorized !== true) return json({ error: 'authorization checkbox required' }, 400);

    const mode = str(b.mode, 20) || null;
    const term_months = [6, 12].includes(Number(b.term_months)) ? Number(b.term_months) : 6;
    const monthly_total = Math.max(0, Math.min(100000, Number(b.monthly_total) || 0));
    const term_total = Math.max(0, Math.min(1200000, Number(b.term_total) || 0));
    const screens = Math.max(0, Math.min(500, Math.round(Number(b.screens) || 0)));
    const est_impressions = Number(b.est_impressions) > 0 ? Math.min(99000000, Number(b.est_impressions)) : null;
    const selection = Array.isArray(b.selection)
      ? b.selection.slice(0, 130).map((s: Record<string, unknown>) => ({
          item: str(s?.item, 160),
          detail: str(s?.detail, 200),
          screens: Math.round(Number(s?.screens) || 0),
          rate: Number(s?.rate) || 0
        }))
      : null;
    const start_date = (typeof b.start_date === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(b.start_date)) ? b.start_date : null;

    const ip = (req.headers.get('x-forwarded-for') ?? '').split(',')[0].trim() || null;
    const ua = str(req.headers.get('user-agent') ?? '', 400) || null;
    const supabase = createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!);

    // Throttle: 5/hr per email, 8/hr per IP
    const hourAgo = new Date(Date.now() - 3600000).toISOString();
    const { count: cEmail } = await supabase.from('contract_requests')
      .select('id', { count: 'exact', head: true })
      .gte('created_at', hourAgo).eq('contact_email', contact_email);
    let cIp = 0;
    if (ip) {
      const { count } = await supabase.from('contract_requests')
        .select('id', { count: 'exact', head: true })
        .gte('created_at', hourAgo).eq('client_ip', ip);
      cIp = count ?? 0;
    }
    if ((cEmail ?? 0) >= 5 || cIp >= 8) {
      return json({ error: 'Too many requests — please call us at 601-405-5054.' }, 429);
    }

    const now = new Date();
    const ref = 'SSA-' + `${now.getUTCFullYear()}${pad(now.getUTCMonth() + 1)}${pad(now.getUTCDate())}` + '-' +
      crypto.randomUUID().replace(/-/g, '').slice(0, 4).toUpperCase();
    const chicagoToday = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Chicago' }).format(now);

    // 1) Record of truth. The row's uuid is what activity_log.entity_id wants
    // (see step 6), so take it on the way in.
    const { data: crRow, error: crErr } = await supabase.from('contract_requests').insert({
      ref,
      quote_ref: str(b.quote_ref, 60) || null,
      business_name, contact_name, contact_email, contact_phone,
      mode, term_months, prepay: !!b.prepay,
      monthly_total, term_total, screens, est_impressions,
      selection, start_date, signed_name,
      agreement_version: str(b.agreement_version, 40) || null,
      quote_link: str(b.quote_link, 2000) || null,
      client_ip: ip, user_agent: ua
    }).select('id').single();
    if (crErr) throw crErr;

    // 2) Legacy quote_submissions inbox (best-effort)
    await supabase.from('quote_submissions').insert({
      quote_ref: str(b.quote_ref, 60) || ref,
      decision: 'accept',
      business_name, contact_name, contact_email, contact_phone,
      mode, term_months, prepay: !!b.prepay,
      monthly_total, term_total, screens, est_impressions,
      selection, user_agent: 'contract-initiate ' + ref
    });

    // 3) Lead on the existing convert-to-client rails (bot id format + suffix vs same-second collisions)
    //
    // leads.industry and leads.contact_phone are both NOT NULL — the intake form
    // always collects them, this flow never does (the agreement modal asks for a
    // business name, not a category, and phone is optional). Send '' the way the
    // intake form does for a skipped field; a null here fails the whole insert,
    // which is silent because this write is best-effort, so the signer lands in
    // contract_requests and never reaches the leads inbox.
    const lead_id = `${now.getUTCFullYear()}${pad(now.getUTCMonth() + 1)}${pad(now.getUTCDate())}_${pad(now.getUTCHours())}${pad(now.getUTCMinutes())}${pad(now.getUTCSeconds())}_${ref.slice(-4)}`;
    const { error: leadErr } = await supabase.from('leads').insert({
      id: lead_id,
      business_name, contact_name, contact_email,
      contact_phone: contact_phone ?? '',
      industry: '',
      status: 'new',
      how_heard: 'Rate Quote Tool (self-serve agreement)',
      additional_notes: `Self-serve SIGNED agreement request ${ref}: $${monthly_total}/mo, ${screens} screens, ${term_months} mo term` +
        (start_date ? `, requested start ${start_date}` : '') + `. Signed by ${signed_name}.`
    });

    // 4) Pipeline opportunity — advertiser vocabulary, contract_sent = awaiting countersign
    const tier_name = (mode === 'pkg' && selection && selection[0]?.item) ? selection[0].item : `Custom — ${screens} screens`;
    const { data: opp } = await supabase.from('pipeline_opportunities').insert({
      lead_id, business_name, contact_name, contact_email, contact_phone,
      source: 'website', deal_type: 'advertiser', stage: 'contract_sent', probability: 90,
      monthly_value: monthly_total, screen_count: screens, tier_name,
      expected_close_date: start_date,
      next_action: `Countersign self-serve agreement ${ref}`,
      next_action_date: chicagoToday,
      notes: `SELF-SERVE signed agreement request ${ref} via rate calculator. ` +
        `$${monthly_total}/mo x ${term_months} mo${b.prepay ? ' PREPAID' : ''}` +
        (start_date ? `, start ${start_date}` : '') + `. Signed: ${signed_name}.`
    }).select('id').single();

    // 5) High-priority task for Creed (UNIQUE(source,source_id) = idempotent)
    await supabase.from('tasks').insert({
      title: `Countersign self-serve agreement — ${business_name} ($${monthly_total}/mo)`,
      description: `${contact_name} (${contact_email}${contact_phone ? ', ' + contact_phone : ''}) signed agreement request ${ref}: ` +
        `$${monthly_total}/mo, ${screens} screens, ${term_months} months${b.prepay ? ' PREPAID' : ''}` +
        (start_date ? `, requested start ${start_date}` : '') +
        `. Review in the bot (Rate Card page, Self-Serve Requests) and countersign within 1 business day.`,
      assigned_to: 'Creed', priority: 'high', due_date: chicagoToday,
      source: 'self_serve', source_id: ref
    });

    // 6) Activity log. entity_id is a uuid column, so it takes the row's id —
    // passing the text ref failed the insert outright, which was invisible
    // because this write is best-effort too. The ref stays in details, which is
    // where anyone looking one up would read it anyway.
    //
    // A failed lead write is recorded here as well, so a silent best-effort
    // miss shows up somewhere other than the function logs.
    await supabase.from('activity_log').insert({
      action: 'Self-serve agreement request received',
      entity_type: 'contract_request', entity_id: crRow?.id ?? null,
      details: {
        ref, business_name, monthly_total, screens, term_months,
        prepay: !!b.prepay, start_date, signed_name, lead_id,
        ...(leadErr ? { lead_insert_error: leadErr.message } : {})
      },
      ip_address: ip
    });

    // 7) Link opportunity back onto the request
    if (opp?.id) {
      await supabase.from('contract_requests').update({ opportunity_id: opp.id, lead_id }).eq('ref', ref);
    } else {
      await supabase.from('contract_requests').update({ lead_id }).eq('ref', ref);
    }

    return json({ ok: true, ref });
  } catch (_e) {
    return json({ error: 'server error — please try again or call 601-405-5054' }, 500);
  }
});
