import requests, os, json
from datetime import date

TOKEN = os.environ['META_ACCESS_TOKEN']
BASE  = "https://graph.facebook.com/v19.0"
WEBNAR_CAMP = "120248546729160002"

SINCE = "2026-05-08"  # Sexta
UNTIL = "2026-05-11"  # Hoje

print(f"=== CAMPANHA WEBNAR — Mafra Lancamento ===")
print(f"Periodo: {SINCE} (sex) → {UNTIL} (seg)\n")

# Total campanha
ins_r = requests.get(f"{BASE}/{WEBNAR_CAMP}/insights", params={
    'fields': 'spend,impressions,clicks,actions,reach,frequency,ctr,cpc,cpm',
    'time_range': json.dumps({'since': SINCE, 'until': UNTIL}),
    'access_token': TOKEN
}, timeout=30)
data = ins_r.json().get('data', [])
if data:
    d = data[0]
    spend = float(d.get('spend', 0))
    leads = 0
    link_clicks = lp_views = 0
    for act in d.get('actions', []):
        t = act.get('action_type', '')
        v = int(act.get('value', 0))
        if t in ('onsite_conversion.lead_grouped', 'lead', 'offsite_conversion.fb_pixel_lead', 'onsite_web_lead'):
            leads = max(leads, v)
        elif t == 'link_click':
            link_clicks = v
        elif t == 'landing_page_view':
            lp_views = v
    cpl = (spend/leads) if leads > 0 else 0
    print(f"  TOTAL CAMPANHA:")
    print(f"    Gasto:    R${spend:,.2f}")
    print(f"    Leads:    {leads}")
    print(f"    CPL:      R${cpl:.2f}")
    print(f"    Impres:   {int(d.get('impressions',0)):,}")
    print(f"    Reach:    {int(d.get('reach',0)):,}")
    print(f"    Freq:     {float(d.get('frequency',0)):.2f}")
    print(f"    CTR:      {float(d.get('ctr',0)):.2f}%")
    print(f"    CPC:      R${float(d.get('cpc',0)):.2f}")
    print(f"    CPM:      R${float(d.get('cpm',0)):.2f}")
    print(f"    Clicks:   {int(d.get('clicks',0)):,} | Link: {link_clicks:,} | LP views: {lp_views:,}")

# Per day breakdown
print(f"\n=== POR DIA ===")
day_r = requests.get(f"{BASE}/{WEBNAR_CAMP}/insights", params={
    'fields': 'spend,impressions,clicks,actions,ctr',
    'time_range': json.dumps({'since': SINCE, 'until': UNTIL}),
    'time_increment': 1,
    'access_token': TOKEN
}, timeout=30)
days = day_r.json().get('data', [])
print(f"{'Data':<12} {'Gasto':>10} {'Leads':>7} {'CPL':>9} {'CTR':>8}")
for d in days:
    sp = float(d.get('spend', 0))
    lds = 0
    for act in d.get('actions', []):
        if act.get('action_type') in ('onsite_conversion.lead_grouped', 'lead', 'offsite_conversion.fb_pixel_lead', 'onsite_web_lead'):
            lds = max(lds, int(act.get('value', 0)))
    cpl = sp/lds if lds > 0 else 0
    print(f"{d.get('date_start')}   R${sp:>7.2f}  {lds:>5}   R${cpl:>5.2f}   {float(d.get('ctr',0)):>5.2f}%")

# Adsets — only those with spend
print(f"\n=== CONJUNTOS COM ENTREGA NO PERIODO ===")
as_r = requests.get(f"{BASE}/{WEBNAR_CAMP}/adsets", params={
    'fields': 'id,name,effective_status,daily_budget',
    'limit': 50, 'access_token': TOKEN
}, timeout=30)
results = []
for a in as_r.json().get('data', []):
    ar = requests.get(f"{BASE}/{a['id']}/insights", params={
        'fields': 'spend,actions,ctr',
        'time_range': json.dumps({'since': SINCE, 'until': UNTIL}),
        'access_token': TOKEN
    }, timeout=30)
    ad = ar.json().get('data', [])
    if not ad: continue
    sp = float(ad[0].get('spend', 0))
    if sp < 0.5: continue
    lds = 0
    for act in ad[0].get('actions', []):
        if act.get('action_type') in ('onsite_conversion.lead_grouped', 'lead', 'offsite_conversion.fb_pixel_lead', 'onsite_web_lead'):
            lds = max(lds, int(act.get('value', 0)))
    cpl = sp/lds if lds > 0 else 0
    results.append({
        'name': a['name'], 'status': a['effective_status'],
        'daily': int(a.get('daily_budget') or 0)/100,
        'spend': sp, 'leads': lds, 'cpl': cpl,
        'ctr': float(ad[0].get('ctr',0))
    })

results.sort(key=lambda x: -x['spend'])
for r in results:
    print(f"  [{r['status']:<8}] {r['name'][:50]}")
    print(f"     Diario: R${r['daily']:.2f}  |  Gasto: R${r['spend']:.2f}  |  Leads: {r['leads']}  |  CPL: R${r['cpl']:.2f}  |  CTR: {r['ctr']:.2f}%\n")
