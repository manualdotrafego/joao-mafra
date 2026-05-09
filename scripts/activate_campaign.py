import requests, os, json, sys

TOKEN = os.environ['META_ACCESS_TOKEN']
BASE  = 'https://graph.facebook.com/v19.0'

# Pause the 2 wrong campaigns
to_pause = ['120249404765890002', '120248861507370002']
for cid in to_pause:
    u = requests.post(f'{BASE}/{cid}', data={'status': 'PAUSED', 'access_token': TOKEN}, timeout=30)
    print(f'Paused {cid}:', u.text)

# Get insights for [NOVA CAPTACAO] - [WEBNAR]
CAMP_ID = '120248546729160002'
print("\n[+] Insights NOVA CAPTACAO WEBNAR (14 dias)...")

ins = requests.get(f'{BASE}/{CAMP_ID}/insights', params={
    'fields': 'date_start,spend,impressions,reach,clicks,actions,cost_per_action_type',
    'date_preset': 'last_14_days',
    'time_increment': 1,
    'limit': 30,
    'access_token': TOKEN
}, timeout=30)
print(json.dumps(ins.json(), indent=2, ensure_ascii=False))

print("\n[+] Por conjunto...")
adset_ins = requests.get(f'{BASE}/{CAMP_ID}/insights', params={
    'fields': 'adset_id,adset_name,spend,impressions,reach,actions,cost_per_action_type',
    'date_preset': 'last_14_days',
    'level': 'adset',
    'limit': 50,
    'access_token': TOKEN
}, timeout=30)
print(json.dumps(adset_ins.json(), indent=2, ensure_ascii=False))
