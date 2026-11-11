"""Pickup reallocation analysis: 11 underutilized store pickups -> lifecycle stores + Canyon Lake."""
import json, sys
sys.path.insert(0, '.')
from load import fuel
from odo import clean_odo
d = json.load(open('data.json')); A = {a['id']: a for a in d['assets']}
C = ['maint', 'fuel_card', 'onsite', 'propane', 'dep', 'reg', 'tax']
RATE, NEW, MONTHS = 995.46, 55000, 10
F = fuel()

# store-to-door pickup ranking (stores 001-121)
by = {}
for a in d['assets']:
    if a.get('pk') == 1 and a['c'] == 'LD Vehicle' and a['s'].isdigit() and 1 <= int(a['s']) <= 121:
        g = by.setdefault(a['s'], [0, 0]); g[0] += sum(sum(a[c]) for c in C); g[1] += sum(a['mi'])
cpm_order = sorted([s for s in by if by[s][1] > 0], key=lambda s: -by[s][0] / by[s][1])
mi_order = sorted([s for s in by if by[s][1] > 0], key=lambda s: by[s][1])
donor_stores = [s for s in cpm_order[:15] if s in mi_order[:15]]

def odo(unit, a):
    o, dt = (None, None) if unit == '600005' else clean_odo(F, int(unit))   # Odessa card shows several vehicles' odometers
    if o: return dict(odo=o, odo_dt=dt, odo_est=False)
    if unit == '601036': return dict(odo=14701.0, odo_dt='2026-08-10', odo_est=False)   # last valid reading; later entries are the unit #
    y, m = int(a['o'][:4]), int(a['o'][5:7]); yrs = ((2026 - y) * 12 + (10 - m)) / 12
    return dict(odo=round(sum(a['mi']) / MONTHS * 12 * yrs), odo_dt='', odo_est=True)

donors = []
for s in donor_stores:
    u = [a for a in d['assets'] if a['s'] == s and a.get('pk') == 1 and a['c'] == 'LD Vehicle' and a['r']][0]
    y, m = int(u['o'][:4]), int(u['o'][5:7]); el = (2026 - y) * 12 + (10 - m) + 1
    ann = lambda keys: sum(sum(u[k]) for k in keys) / MONTHS * 12
    donors.append(dict(store=s, name=d['stores'][s]['name'], dist=d['stores'][s]['district'], unit=u['id'], orig=u['o'], cost=u['cost'],
        mi=sum(u['mi']), annmi=sum(u['mi']) / MONTHS * 12, cpm=by[s][0] / by[s][1], rank=cpm_order.index(s) + 1, mirank=mi_order.index(s) + 1,
        ex=ann(['maint', 'dep', 'reg', 'tax']), fuel=ann(['fuel_card']), dep=ann(['dep']), maint=ann(['maint']), regtax=ann(['reg', 'tax']),
        nbv=max(0, u['cost'] - u['cost'] / 60 * el), **odo(u['id'], u)))

# receiving stores, ordered by current annual miles (new store last)
REC = [('450', '599007'), ('52', '599003'), ('63', '598008'), ('8', '596007'), ('117', '599030'), ('67', '600006'),
       ('18', '596002'), ('53', '599025'), ('70', '597002'), ('90', '594179'), ('122', None)]
recs = []
for s, ru in REC:
    r = A.get(ru) if ru else None
    o = clean_odo(F, int(ru))[0] if ru else None
    recs.append(dict(store=s, name=d['stores'].get(s, {}).get('name', 'Canyon Lake'), repl=ru, repl_o=r['o'] if r else '',
                     repl_annmi=sum(r['mi']) / MONTHS * 12 if r else None, repl_odo=o, why='Fleet Lifecycle' if ru else 'Fleet Addition - New Store'))
recs.sort(key=lambda r: -(r['repl_annmi'] or -1))
# lowest-mileage trucks go to the highest-usage receiving stores
for dn, rc in zip(sorted(donors, key=lambda x: x['odo']), recs):
    dn['to'] = rc
json.dump(dict(rate=RATE, new_truck=NEW, rates=d['rates'], donors=donors, built='2026-11-11'), open('proposal.json', 'w'))
for dn in sorted(donors, key=lambda x: x['odo']):
    print(dn['store'], dn['name'], dn['unit'], int(dn['odo']), 'est' if dn['odo_est'] else '', '->', dn['to']['store'], dn['to']['name'], dn['to']['repl'], dn['to']['repl_odo'], round(dn['to']['repl_annmi'] or 0))
print(len(donors), 'billing', RATE * 12 * len(donors), 'ex', round(sum(x['ex'] for x in donors)))
