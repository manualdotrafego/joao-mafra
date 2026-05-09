import requests, os, json, sys
from datetime import datetime, timedelta

TOKEN = os.environ['META_ACCESS_TOKEN']
BASE  = 'https://graph.facebook.com/v19.0'

CAMP_ID = '120248546729160002'
since = (datetime.now() - timedelta(days=14)).strftime('%Y-%m-%d')
until = datetime.now().strftime('%Y-%m-%d')

print(f"[+] Insights NOVA CAPTACAO WEBNAR ({since} -> {until})...")

ins = requests.get(f'{BASE}/{CAMP_ID}/insights', params={
    'fields': 'date_start,spend,impressions,reach,clicks,actions,cost_per_action_type',
    'since': since,
    'until': until,
    'time_increment': 1,
    'limit': 30,
    'access_token': TOKEN
}, timeout=30)
print(json.dumps(ins.json(), indent=2, ensure_ascii=False))

print("\n[+] Adset breakdown...")
adset_ins = requests.get(f'{BASE}/{CAMP_ID}/insights', params={
    'fields': 'adset_id,adset_name,spend,impressions,reach,clicks,actions',
    'since': since,
    'until': until,
    'level': 'adset',
    'limit': 50,
    'access_token': TOKEN
}, timeout=30)
print(json.dumps(adset_ins.json(), indent=2, ensure_ascii=False))
