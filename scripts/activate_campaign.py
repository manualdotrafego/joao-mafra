import requests, os, json, sys

TOKEN = os.environ['META_ACCESS_TOKEN']
BASE  = 'https://graph.facebook.com/v19.0'
ACCT  = 'act_615338413578534'
KEYWORD = os.environ.get('CAMP_KEYWORD', 'webnar').lower()

print(f"[+] Buscando campanha com '{KEYWORD}'...")

r = requests.get(f'{BASE}/{ACCT}/campaigns', params={
    'fields': 'id,name,status,effective_status,daily_budget,lifetime_budget',
    'limit': 100,
    'access_token': TOKEN
}, timeout=30)
data = r.json()

if 'error' in data:
    print('ERRO:', data['error']['message']); sys.exit(1)

campaigns = data.get('data', [])
targets = [c for c in campaigns if KEYWORD in c['name'].lower()]
print(f"Encontradas: {len(targets)}")
for c in targets:
    print(f"  {c['id']} | {c.get('effective_status')} | {c['name']}")

if not targets:
    print('Nenhuma campanha encontrada.'); sys.exit(1)

# Activate each found campaign
for c in targets:
    camp_id = c['id']
    cur_status = c.get('status')
    print(f"\n[~] Ativando {camp_id} ({cur_status} -> ACTIVE)...")
    u = requests.post(f'{BASE}/{camp_id}', data={
        'status': 'ACTIVE',
        'access_token': TOKEN
    }, timeout=30)
    print('[POST]', u.text)
    if u.ok and 'success' in u.text:
        print(f'OK: Campanha ativada!')
    else:
        print('WARN:', u.text)

# Get last 10 days insights
print("\n[+] Buscando insights dos ultimos 10 dias...")
for c in targets:
    camp_id = c['id']
    ins = requests.get(f'{BASE}/{camp_id}/insights', params={
        'fields': 'spend,impressions,reach,clicks,actions,video_play_actions,video_p25_watched_actions,video_p50_watched_actions,video_p75_watched_actions,video_p100_watched_actions',
        'date_preset': 'last_14_days',
        'time_increment': 1,
        'limit': 30,
        'access_token': TOKEN
    }, timeout=30)
    print(f"\n--- INSIGHTS {c['name'][:40]} ---")
    print(json.dumps(ins.json(), indent=2, ensure_ascii=False))
