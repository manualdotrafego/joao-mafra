import requests, os, json

TOKEN = os.environ['META_ACCESS_TOKEN']
BASE  = "https://graph.facebook.com/v19.0"
WEBNAR_CAMP = "120248546729160002"

SINCE = "2026-05-08"  # Sexta-feira
UNTIL = "2026-05-11"  # Hoje (Segunda)

print(f"=== WEBNAR — Conjuntos (sex {SINCE} → seg {UNTIL}) ===\n")

# 1. Get all adsets in WEBNAR campaign
r = requests.get(f"{BASE}/{WEBNAR_CAMP}/adsets", params={
    'fields': 'id,name,status,effective_status,daily_budget,lifetime_budget',
    'limit': 100, 'access_token': TOKEN
}, timeout=30)
adsets = r.json().get('data', [])
print(f"Total conjuntos: {len(adsets)}\n")

# 2. Get insights for each adset in the date range
results = []
for a in adsets:
    aid = a['id']
    name = a['name']
    status = a.get('effective_status')
    db = int(a.get('daily_budget') or 0)
    
    # Get insights
    ins_r = requests.get(f"{BASE}/{aid}/insights", params={
        'fields': 'spend,impressions,clicks,actions,cost_per_action_type,cpc,cpm,ctr',
        'time_range': json.dumps({'since': SINCE, 'until': UNTIL}),
        'access_token': TOKEN
    }, timeout=30)
    ins = ins_r.json().get('data', [])
    
    spend = 0
    leads = 0
    impressions = 0
    clicks = 0
    if ins:
        d = ins[0]
        spend = float(d.get('spend', 0))
        impressions = int(d.get('impressions', 0))
        clicks = int(d.get('clicks', 0))
        # Find leads in actions
        for act in d.get('actions', []):
            t = act.get('action_type', '')
            if t in ('onsite_conversion.lead_grouped', 'lead', 'offsite_conversion.fb_pixel_lead', 'onsite_web_lead'):
                leads = max(leads, int(act.get('value', 0)))
    
    cpl = (spend / leads) if leads > 0 else 0
    ctr = (clicks / impressions * 100) if impressions > 0 else 0
    
    results.append({
        'id': aid,
        'name': name,
        'status': status,
        'daily': db / 100,
        'spend': spend,
        'leads': leads,
        'cpl': cpl,
        'imps': impressions,
        'clicks': clicks,
        'ctr': ctr,
    })

# Sort: ACTIVE first, then by spend desc
results.sort(key=lambda x: (x['status'] != 'ACTIVE', -x['spend']))

# Print table
total_spend = total_leads = 0
for r in results:
    if r['spend'] == 0 and r['leads'] == 0:
        continue
    total_spend += r['spend']
    total_leads += r['leads']
    print(f"[{r['status']}] {r['name'][:60]}")
    print(f"  id={r['id']} | daily=R${r['daily']:.2f}")
    print(f"  Gasto: R${r['spend']:.2f} | Leads: {r['leads']} | CPL: R${r['cpl']:.2f}")
    print(f"  Imps: {r['imps']:,} | Clicks: {r['clicks']:,} | CTR: {r['ctr']:.2f}%")
    print()

# Show inactive/zero
print("=== Conjuntos sem dados no periodo ===")
for r in results:
    if r['spend'] == 0 and r['leads'] == 0:
        print(f"  [{r['status']}] {r['name'][:60]} | id={r['id']}")

print(f"\n=== TOTAL CAMPANHA WEBNAR (sex→hoje) ===")
print(f"Gasto: R${total_spend:.2f}")
print(f"Leads: {total_leads}")
if total_leads > 0:
    print(f"CPL medio: R${total_spend/total_leads:.2f}")
