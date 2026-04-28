import requests, json, os, time
from datetime import datetime, timedelta, timezone, date as date_cls
from collections import defaultdict
import urllib.request

TOKEN = os.environ['META_ACCESS_TOKEN']
BASE  = "https://graph.facebook.com/v19.0"
ACCT  = "act_615338413578534"   # CA - João Mafra Lançamento

now   = datetime.now(timezone.utc)
UNTIL = now.strftime("%Y-%m-%d")
SINCE = (now - timedelta(days=29)).strftime("%Y-%m-%d")  # 30 dias contando hoje

DISPLAY_NAME     = "CA - João Mafra Lançamento"
LEAD_OBJECTIVES  = ["LEAD_GENERATION", "OUTCOME_LEADS"]

os.makedirs("docs-joao/thumbnails", exist_ok=True)

# ── Lead deduplication (priority-based) ───────────────────────────────────────
LEAD_PRIORITY = [
    'onsite_conversion.lead_grouped',
    'lead',
    'offsite_conversion.fb_pixel_lead',
    'onsite_web_lead',
]
WA_ACTION   = 'omni_initiated_checkout'
FORM_ACTION = 'add_to_wishlist'

# ── Helpers ────────────────────────────────────────────────────────────────────
def get(url, params=None):
    p = dict(params or {}); p['access_token'] = TOKEN
    r = requests.get(url, params=p, timeout=30)
    if not r.ok:
        print(f"  ERR {r.status_code}: {r.text[:200]}")
        return {}
    return r.json()

def paginate(url, params=None, max_pages=30):
    results, page, data = [], 0, get(url, params)
    results.extend(data.get('data', []))
    while data.get('paging', {}).get('next') and page < max_pages:
        time.sleep(0.2)
        data = get(data['paging']['next'])
        results.extend(data.get('data', []))
        page += 1
    return results

def extract_leads(actions):
    acts = actions or []
    for atype in LEAD_PRIORITY:
        val = sum(float(a.get('value', 0)) for a in acts if a.get('action_type') == atype)
        if val > 0:
            return val
    return 0

def extract_action(actions, atype):
    return sum(float(a.get('value', 0)) for a in (actions or [])
               if a.get('action_type') == atype)

def extract_video_views(actions):
    return sum(float(a.get('value', 0)) for a in (actions or [])
               if a.get('action_type') == 'video_view')

def extract_arr(arr):
    return sum(float(v.get('value', 0)) for v in (arr or []))

def safe_div(a, b, mult=1):
    return (a / b) * mult if b > 0 else 0

def proc(d):
    spend  = float(d.get('spend', 0))
    impr   = int(d.get('impressions', 0))
    clicks = int(d.get('clicks', 0))
    reach  = int(d.get('reach', 0))
    acts   = d.get('actions', [])
    leads  = extract_leads(acts)
    vviews = extract_video_views(acts)
    contact  = extract_action(acts, WA_ACTION)
    wishlist = extract_action(acts, FORM_ACTION)
    p25  = extract_arr(d.get('video_p25_watched_actions',  []))
    p50  = extract_arr(d.get('video_p50_watched_actions',  []))
    p75  = extract_arr(d.get('video_p75_watched_actions',  []))
    p100 = extract_arr(d.get('video_p100_watched_actions', []))
    return {
        'spend':       round(spend, 2),
        'impressions': impr,
        'clicks':      clicks,
        'reach':       reach,
        'leads':       int(leads),
        'ctr':         round(float(d.get('ctr', 0)), 2),
        'cpc':         round(float(d.get('cpc', 0)), 2),
        'cpm':         round(float(d.get('cpm', 0)), 2),
        'cpl':         round(safe_div(spend, leads), 2),
        'lp_conv':     round(safe_div(leads, clicks, 100), 1),
        'hook_rate':   round(safe_div(vviews, impr, 100), 1),
        'vp25':        round(safe_div(p25,  impr, 100), 1),
        'vp50':        round(safe_div(p50,  impr, 100), 1),
        'vp75':        round(safe_div(p75,  impr, 100), 1),
        'vp100':       round(safe_div(p100, impr, 100), 1),
        'wa_group':    int(contact),
        'cp_wa':       round(safe_div(spend, contact), 2),
        'form_thanks': int(wishlist),
        'cp_form':     round(safe_div(spend, wishlist), 2),
    }

def empty_day(date_str):
    return {'date': date_str, 'spend': 0, 'impressions': 0, 'clicks': 0,
            'reach': 0, 'leads': 0, 'ctr': 0, 'cpc': 0, 'cpm': 0,
            'cpl': 0, 'lp_conv': 0, 'hook_rate': 0,
            'vp25': 0, 'vp50': 0, 'vp75': 0, 'vp100': 0,
            'wa_group': 0, 'cp_wa': 0, 'form_thanks': 0, 'cp_form': 0}

INS_FIELDS = ('spend,impressions,clicks,reach,ctr,cpc,cpm,actions,'
              'video_p25_watched_actions,video_p50_watched_actions,'
              'video_p75_watched_actions,video_p100_watched_actions')

# Build full 30-day date list
since_date = date_cls.fromisoformat(SINCE)
until_date = date_cls.fromisoformat(UNTIL)
all_dates  = []
d = since_date
while d <= until_date:
    all_dates.append(d.isoformat())
    d += timedelta(days=1)

# ─── 0. Account info ──────────────────────────────────────────────────────────
print("0/7 Account info...")
acct = get(f"{BASE}/{ACCT}", {'fields': 'name,currency,account_status'})
print(f"   {acct.get('name')} | {acct.get('currency')}")

# ─── 1. Active lead campaigns ─────────────────────────────────────────────────
print("1/7 Campanhas de lead ativas...")
all_camps_raw = paginate(f"{BASE}/{ACCT}/campaigns", {
    'fields': 'id,name,objective,effective_status',
    'filtering': json.dumps([
        {"field": "objective",        "operator": "IN", "value": LEAD_OBJECTIVES},
        {"field": "effective_status", "operator": "IN", "value": ["ACTIVE", "PAUSED"]},
    ]),
    'limit': 100,
})
target_camp_ids = [c['id'] for c in all_camps_raw]
status_map = {c['id']: c.get('effective_status', '?') for c in all_camps_raw}

if not target_camp_ids:
    print("   ⚠ Nenhuma campanha de lead ativa. Usando todas com gasto.")
    CAMP_FILTER = json.dumps([{"field": "spend", "operator": "GREATER_THAN", "value": 0}])
else:
    CAMP_FILTER = json.dumps([{"field": "campaign.id", "operator": "IN", "value": target_camp_ids}])
    print(f"   {len(target_camp_ids)} campanhas de lead")
    for c in all_camps_raw:
        print(f"   [{c.get('effective_status','?')[:6]}] {c['name'][:70]}")

print(f"   Janela: {len(all_dates)} dias ({SINCE} → {UNTIL})")

# ─── 2. Account daily + summary ───────────────────────────────────────────────
print("2/7 Daily insights (30d)...")
raw_daily = paginate(f"{BASE}/{ACCT}/insights", {
    'fields': INS_FIELDS,
    'time_range': json.dumps({'since': SINCE, 'until': UNTIL}),
    'time_increment': 1, 'level': 'account',
    'filtering': CAMP_FILTER,
    'limit': 100,
})
raw_sum = get(f"{BASE}/{ACCT}/insights", {
    'fields': INS_FIELDS,
    'time_range': json.dumps({'since': SINCE, 'until': UNTIL}),
    'level': 'account',
    'filtering': CAMP_FILTER,
}).get('data', [{}])

daily_by_date = {r.get('date_start', ''): r for r in raw_daily}
daily = []
for date in all_dates:
    if date in daily_by_date:
        row = proc(daily_by_date[date]); row['date'] = date
    else:
        row = empty_day(date)
    daily.append(row)

summary = proc(raw_sum[0] if raw_sum else {})
print(f"   Gasto: R$ {summary['spend']} | Leads: {summary['leads']} | "
      f"WA: {summary['wa_group']} | Forms: {summary['form_thanks']}")

# ─── 3. Campaign insights ─────────────────────────────────────────────────────
print("3/7 Campaign insights...")
camp_sum_raw = paginate(f"{BASE}/{ACCT}/insights", {
    'fields': 'campaign_id,campaign_name,' + INS_FIELDS,
    'time_range': json.dumps({'since': SINCE, 'until': UNTIL}),
    'level': 'campaign', 'filtering': CAMP_FILTER, 'limit': 100,
})
camp_daily_raw = paginate(f"{BASE}/{ACCT}/insights", {
    'fields': 'campaign_id,' + INS_FIELDS,
    'time_range': json.dumps({'since': SINCE, 'until': UNTIL}),
    'time_increment': 1, 'level': 'campaign',
    'filtering': CAMP_FILTER, 'limit': 500,
})
camp_daily_map = defaultdict(dict)
for r in camp_daily_raw:
    cid  = r.get('campaign_id', '')
    date = r.get('date_start', '')
    row  = proc(r); row['date'] = date
    camp_daily_map[cid][date] = row
print(f"   {len(camp_sum_raw)} campanhas")

# ─── 4. Adset insights ────────────────────────────────────────────────────────
print("4/7 Adset insights...")
adset_sum_raw = paginate(f"{BASE}/{ACCT}/insights", {
    'fields': 'campaign_id,adset_id,adset_name,' + INS_FIELDS,
    'time_range': json.dumps({'since': SINCE, 'until': UNTIL}),
    'level': 'adset', 'filtering': CAMP_FILTER, 'limit': 200,
})
adsets_by_camp = defaultdict(list)
seen_adsets = set()
for r in adset_sum_raw:
    asid = r.get('adset_id', '')
    if asid in seen_adsets:
        continue
    seen_adsets.add(asid)
    row = proc(r)
    row['id']          = asid
    row['name']        = r.get('adset_name', '')
    row['campaign_id'] = r.get('campaign_id', '')
    adsets_by_camp[r.get('campaign_id', '')].append(row)
print(f"   {len(adset_sum_raw)} conjuntos")

# ─── 5. Ad insights ───────────────────────────────────────────────────────────
print("5/7 Ad insights...")
ad_raw = paginate(f"{BASE}/{ACCT}/insights", {
    'fields': 'ad_id,ad_name,campaign_id,campaign_name,adset_id,adset_name,' + INS_FIELDS,
    'time_range': json.dumps({'since': SINCE, 'until': UNTIL}),
    'level': 'ad', 'filtering': CAMP_FILTER, 'limit': 200,
})
print(f"   {len(ad_raw)} ads com gasto")

# ─── 6. Thumbnails ────────────────────────────────────────────────────────────
print("6/7 Thumbnails...")
ads_by_adset = defaultdict(list)
seen_ads = set()
for r in ad_raw:
    aid = r.get('ad_id', '')
    if aid in seen_ads:
        continue
    seen_ads.add(aid)
    row = proc(r)
    row.update({
        'id':          aid,
        'name':        r.get('ad_name', ''),
        'campaign_id': r.get('campaign_id', ''),
        'adset_id':    r.get('adset_id', ''),
        'adset_name':  r.get('adset_name', ''),
        'thumbnail':   '',
        'video_id':    '',
        'preview_url': '',
    })
    time.sleep(0.1)
    cr = get(f"{BASE}/{aid}", {
        'fields': 'creative{thumbnail_url,video_id,object_story_id}'
    })
    creative  = cr.get('creative', {})
    thumb_url = creative.get('thumbnail_url', '')
    video_id  = creative.get('video_id', '')
    story_id  = creative.get('object_story_id', '')
    row['video_id'] = video_id or ''

    if video_id:
        row['preview_url'] = f"https://www.facebook.com/watch?v={video_id}"
    elif story_id and '_' in story_id:
        parts = story_id.split('_', 1)
        row['preview_url'] = (f"https://www.facebook.com/permalink.php"
                              f"?story_fbid={parts[1]}&id={parts[0]}")

    if not thumb_url and video_id:
        vid = get(f"{BASE}/{video_id}", {'fields': 'thumbnails'})
        thumbs = vid.get('thumbnails', {}).get('data', [])
        if thumbs:
            thumb_url = thumbs[0].get('uri', '')

    if thumb_url:
        fname = f"docs-joao/thumbnails/{aid}.jpg"
        try:
            sep    = '&' if '?' in thumb_url else '?'
            dl_url = thumb_url + sep + f'access_token={TOKEN}'
            req    = urllib.request.Request(dl_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as resp:
                with open(fname, 'wb') as f:
                    f.write(resp.read())
            row['thumbnail'] = f'thumbnails/{aid}.jpg'
        except Exception as e:
            print(f"   ⚠ thumb {aid}: {e}")

    ads_by_adset[r.get('adset_id', '')].append(row)

for asid in ads_by_adset:
    ads_by_adset[asid].sort(key=lambda x: x['spend'], reverse=True)

n_thumb = sum(1 for lst in ads_by_adset.values() for a in lst if a['thumbnail'])
print(f"   {n_thumb} thumbnails baixadas")

# ─── 7. Build nested structure + integrity check ──────────────────────────────
print("7/7 Salvando JSON...")

campaigns = []
seen_camps = set()
for r in camp_sum_raw:
    cid = r.get('campaign_id', '')
    if cid in seen_camps:
        print(f"   ⚠ campanha duplicada: {cid}")
        continue
    seen_camps.add(cid)
    row = proc(r)
    row['id']     = cid
    row['name']   = r.get('campaign_name', '')
    row['status'] = status_map.get(cid, '?')
    row['daily']  = [camp_daily_map[cid].get(date, empty_day(date)) for date in all_dates]

    # Adsets com ads aninhados
    camp_adsets = sorted(adsets_by_camp.get(cid, []), key=lambda x: x['spend'], reverse=True)
    for adset in camp_adsets:
        adset['ads'] = sorted(ads_by_adset.get(adset['id'], []),
                              key=lambda x: x['spend'], reverse=True)
    row['adsets'] = camp_adsets
    campaigns.append(row)

campaigns.sort(key=lambda x: x['spend'], reverse=True)

# Integrity check
active_days = [d for d in daily if d['spend'] > 0]
daily_sum   = round(sum(d['spend'] for d in active_days), 2)
delta       = abs(daily_sum - summary['spend'])
emoji       = '✅' if delta <= 0.05 else '⚠'
print(f"   {emoji} daily_sum={daily_sum} | summary={summary['spend']} | "
      f"WA={summary['wa_group']} | Forms={summary['form_thanks']}")

total_adsets = sum(len(c['adsets']) for c in campaigns)
total_ads    = sum(len(a['ads']) for c in campaigns for a in c['adsets'])

data = {
    'last_updated': now.strftime('%Y-%m-%dT%H:%M:%SZ'),
    'account':      {'id': ACCT, 'name': DISPLAY_NAME, 'currency': acct.get('currency', 'BRL')},
    'date_range':   {'since': SINCE, 'until': UNTIL},
    'summary':      summary,
    'daily':        daily,
    'campaigns':    campaigns,
}
with open('docs-joao/data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\n✅ docs-joao/data.json salvo")
print(f"   {len(campaigns)} campanhas | {total_adsets} conjuntos | {total_ads} ads | {len(daily)} dias")
print(f"   30d: {acct.get('currency','BRL')} {summary['spend']} | Leads: {summary['leads']} | CPL: {summary['cpl']}")
