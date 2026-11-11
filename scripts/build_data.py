"""Build the asset-month cost dataset for the McCoy's YTD cost-per-mile report."""
import sys, json, re
sys.path.insert(0, '.')
import numpy as np
from load import *

M = list(range(1, 11))
MN = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct']
LIFE = {'Truck': 60, 'LD Vehicle': 60, 'Trailer': 60, 'TMFL': 84, 'Forklift': 84, 'Ancillary Fleet': 84}
REG_CLASSES = {'Truck', 'LD Vehicle', 'Trailer'}
TAX_RATE, REG_RATE = 0.000667, 0.0005
notes = []          # data-issue rows for the report

def sc(v):
    """normalize a store code"""
    s = str(v).strip()
    if s in ('', 'nan', 'None'): return None
    s = s.split('.')[0] if re.fullmatch(r'\d+\.0', s) else s
    return s.lstrip('0') or '0'

# ---------------------------------------------------------------- stores
R['store'] = R['Store Number'].map(sc)
stores = {}
for _, r in R.drop_duplicates('store').iterrows():
    stores[r.store] = {'name': r['Store Name'], 'district': r['Store District'] if isinstance(r['Store District'], str) else 'Other'}
prop_raw = pd.read_excel(U + 'cb200497-Propane_2027_by_Location_Month.xlsx', sheet_name='Cost')
prop_raw = prop_raw[prop_raw.Location.notna()].copy()
prop_raw['store'] = prop_raw.Location.map(sc)
for _, r in prop_raw.iterrows():
    stores.setdefault(r.store, {'name': r.Name, 'district': r.District})
SP = pd.read_excel(U + 'b7574e76-Asset_Spend_Data_2026_17.xlsx')
SP['store'] = SP['Work Order Store Identifier'].astype(str).str.split(' ').str[0].map(sc)
for code, ident in SP[['store', 'Work Order Store Identifier']].drop_duplicates('store').values:
    stores.setdefault(code, {'name': str(ident).split(' ', 1)[1] if ' ' in str(ident) else str(ident), 'district': 'Other'})
def ensure_store(code):
    if code and code not in stores:
        stores[code] = {'name': f'Location {code}', 'district': 'Other'}

# ---------------------------------------------------------------- sources
F = fuel(); F['acct'] = F['Account Name'].map(sc)
Mi = miles(); Mi['Store'] = Mi['Store'].map(sc)
Mi.loc[~Mi['Store'].astype(str).str.fullmatch(r'\d{1,3}[A-Z]{0,2}'), 'Store'] = None  # telematics groups like 'Sale Pending'
H = hours()
D = pd.read_excel(U + 'eed968bc-BA_-_McCoys_Asset_Depreciation_Forecast_Fleet_Detail.xlsx', sheet_name=1)
D['Unit'] = pd.to_numeric(D['Asset Identifier'], errors='coerce')
D['store'] = D['Cost Center'].astype(str).str.split(' ').str[0].map(sc)
tmpl = pd.read_excel(U + 'c06aef92-Current_Assets_10_31_2026.xlsx', sheet_name=1, header=3)
TMPL = {str(a).strip(): str(b).strip() for a, b in zip(tmpl.iloc[:, 0], tmpl.iloc[:, 1]) if isinstance(a, str)}

# ---------------------------------------------------------------- asset master
A = {}   # id -> dict
roster_ids = set(R['Asset Name'])
for _, r in R.iterrows():
    owned = r['Asset Ownership'] == 'Company Owned'
    cost = r['Asset Original Value'] if pd.notna(r['Asset Original Value']) and r['Asset Original Value'] > 0 else None
    od = pd.to_datetime(r['Asset Date of Origination'])
    A[int(r['Asset Name'])] = dict(id=int(r['Asset Name']), store=r.store, cls=r['Asset Class'], type=r['Asset Template Name'],
        make=r['Asset Manufacturer Name'] if isinstance(r['Asset Manufacturer Name'], str) else '', owned=owned, cost=cost,
        orig=od.strftime('%Y-%m-%d'), status=r['Asset Status'], roster=True, costsrc='Roster' if cost else None)

suffix_cls = {'pup': 'LD Vehicle', 'flb': 'Truck', 'ttr': 'Truck', 'vnb': 'Truck', 'conv': 'Truck', 'van': 'LD Vehicle'}
def cls_from_vehicle(v):
    for tok in str(v).lower().split('-'):
        if tok in suffix_cls: return suffix_cls[tok]
    return None

def add_nonroster(uid, cls=None, typ=None):
    if uid in A:
        a = A[uid]
        if a['cls'] is None and cls: a['cls'] = cls
        if not a['type'] and typ: a['type'] = typ
        return
    A[uid] = dict(id=uid, store=None, cls=cls, type=typ or '', make='', owned=True, cost=None, orig='', status='Disposed / not on 10/31 roster',
                  roster=False, costsrc=None)

# spend: invoice splitting + exclusions
amt = 'Subcontractor Invoice Total'
SP['dt'] = pd.to_datetime(SP['Subcontractor Invoice Transaction Date'], format='mixed'); SP['Month'] = SP.dt.dt.month
key = ['Subcontractor Invoice Reference Number', amt, 'Work Order ID']
SP['n_assets'] = SP.groupby(key)['Asset Name'].transform('size')
SP['amt'] = SP[amt] / SP['n_assets']
SP['sub'] = SP['Work Order Category Full Path'].str.split(r' \| ').str[-1].str.split(' - ').str[-1]
SP['cat'] = SP['Work Order Category Full Path'].str.split(r' \| ').str[1]
SP['Unit'] = pd.to_numeric(SP['Asset Name'], errors='coerce')
REGTAX_SUBS = {'Registration-Inspection', 'Personal Property Tax', 'Monthly Registration Invoice'}
NONFLEET_CATS = {'Insulation Blower', 'Holtec Saw', 'Ancillary Materials'}
SP['bucket'] = 'asset'
SP.loc[SP['sub'].isin(REGTAX_SUBS), 'bucket'] = 'regtax_excluded'
SP.loc[(SP['bucket'] == 'asset') & (SP['cat'].isin(NONFLEET_CATS) | SP.Unit.isna()), 'bucket'] = 'nonfleet'
split_extra = (SP[amt] - SP['amt']).sum()

for _, r in SP[(SP.bucket == 'asset') & ~SP.Unit.isin(roster_ids)].drop_duplicates('Unit').iterrows():
    add_nonroster(int(r.Unit), TMPL.get(str(r['Asset Template Name']).strip()), r['Asset Template Name'])
for _, r in Mi[Mi.Unit.notna() & ~Mi.Unit.isin(roster_ids)].drop_duplicates('Unit').iterrows():
    add_nonroster(int(r.Unit), cls_from_vehicle(r.Vehicle))
for _, r in F[F.Unit.notna() & ~F.Unit.isin(roster_ids)].drop_duplicates('Unit').iterrows():
    add_nonroster(int(r.Unit), 'Truck' if 'Diesel' in str(r['Product Description']) else 'LD Vehicle')
for _, r in H[~H.Unit.isin(roster_ids)].drop_duplicates('Unit').iterrows():
    add_nonroster(int(r.Unit), 'TMFL' if r.Fleet == 'TMFL' else 'Forklift')
book_cls = lambda c: 'Forklift' if 'Forklift' in c else ('LD Vehicle' if 'Light' in c else 'Truck')
for _, r in D[D.Unit.notna() & ~D.Unit.isin(roster_ids)].drop_duplicates('Unit').iterrows():
    add_nonroster(int(r.Unit), book_cls(str(r['Spend Category'])))

# rental / sub units without a unit number (telematics only)
rent = Mi.Unit.isna()
Mi['aid'] = [('RENT:' + str(v)) if r else int(u) for u, v, r in zip(Mi.Unit, Mi.Vehicle, rent)]
for v, s in Mi.loc[rent, ['aid', 'Store']].drop_duplicates('aid').values:
    A[v] = dict(id=v, store=s, cls='Truck', type='Sub / rental unit', make='', owned=False, cost=None, orig='', status='Rental / sub (no unit #)',
                roster=False, costsrc=None)

# store for non-roster units: latest telematics store > fuel account > spend WO store > hours location > book cost center
def latest(df, idcol, storecol, uid):
    x = df[df[idcol] == uid]
    x = x[x[storecol].notna()]
    return x.sort_values('Month')[storecol].iloc[-1] if len(x) else None
H['store'] = H.Location.map(sc)
for uid, a in A.items():
    if a['store'] is None:
        a['store'] = (latest(Mi, 'aid', 'Store', uid) or latest(F, 'Unit', 'acct', uid) or latest(SP, 'Unit', 'store', uid)
                      or latest(H, 'Unit', 'store', uid) or (D.loc[D.Unit == uid, 'store'].iloc[0] if (D.Unit == uid).any() else None) or 'UNK')
    if a['cls'] is None: a['cls'] = 'Truck'
    ensure_store(a['store'])

# ---------------------------------------------------------------- monthly grids
def grid(): return {}
def add(g, aid, m, v):
    g.setdefault(aid, np.zeros(10))[m - 1] += v

maint, fcard, onsite, propane, dep, reg, tax, mil, hrs = (grid() for _ in range(9))
mil_est, hrs_est = {}, {}
loc_level = {}   # (store, component) -> np array  (costs that cannot be tied to an asset)
def add_loc(store, comp, m, v):
    ensure_store(store)
    loc_level.setdefault((store, comp), np.zeros(10))[m - 1] += v

# maintenance
for r in SP[SP.bucket == 'asset'].itertuples():
    add(maint, int(r.Unit), r.Month, r.amt)
nonfleet = SP[SP.bucket == 'nonfleet']
regtax_ex = SP[SP.bucket == 'regtax_excluded']

# fuel card
g =F[F.Unit.notna()].groupby(['Unit', 'Month'])['Net Cost'].sum()
for (u, m), v in g.items(): add(fcard, int(u), m, v)
gen = F[F.Unit.isna()].groupby(['acct', 'Month'])['Net Cost'].sum()
for (s, m), v in gen.items(): add_loc(s, 'fuel_card', m, v)

# miles (+ gap fill: unit reported in month m-1 and m+1 but not m -> average)
g = Mi.groupby(['aid', 'Month'])['Distance'].sum()
for (u, m), v in g.items(): add(mil, u, m, v)
filled = []
for u, arr in mil.items():
    present = {m for m in M if ((u, m) in g.index)}
    for m in range(2, 10):
        if m not in present and (m - 1) in present and (m + 1) in present:
            arr[m - 1] = (arr[m - 2] + arr[m]) / 2
            mil_est.setdefault(u, set()).add(m); filled.append((u, m, arr[m - 1]))
filled_df = pd.DataFrame(filled, columns=['aid', 'Month', 'Miles'])

# hours
for r in H.itertuples():
    add(hrs, r.Unit, r.Month, r.Hours)
hours_actual_units = set(H.loc[H['Months Actual'] > 0, 'Unit'])

# active months
def months_active(a):
    uid = a['id']
    if a['roster']:
        od = pd.to_datetime(a['orig'])
        start = 1 if od.year < 2026 else od.month
        return set(range(start, 11))
    act = set()
    for gg in (maint, fcard, mil, hrs):
        if uid in gg: act |= {m for m in M if gg[uid][m - 1] != 0}
    if not act and uid in set(D.Unit.dropna()):
        act = {1, 2, 3}  # in service per March book, no activity found
    return set(range(min(act), max(act) + 1)) if act else set()
for a in A.values():
    a['active'] = sorted(months_active(a))

# depreciation & registration / taxes
book = D[D.Unit.notna()].groupby('Unit')['Depreciation Amount'].sum()
book_cat = D[D.Unit.notna()].groupby('Unit')['Spend Category'].first()
for uid, a in A.items():
    act = a['active']
    if not act: continue
    if a['roster']:
        if a['owned'] and a['cost']:
            od = pd.to_datetime(a['orig']); life = LIFE[a['cls']]
            for m in act:
                mi = (2026 - od.year) * 12 + (m - od.month)
                if 0 <= mi < life: add(dep, uid, m, a['cost'] / life)
        a['fully_dep'] = bool(a['owned'] and a['cost'] and ((2026 - pd.to_datetime(a['orig']).year) * 12 + (10 - pd.to_datetime(a['orig']).month)) >= LIFE[a['cls']])
    elif isinstance(uid, int) and uid in book.index:
        life = 84 if 'Forklift' in str(book_cat[uid]) else 60
        a['cost'] = round(float(book[uid]) * life, 2); a['costsrc'] = 'Implied from Mar-26 book depreciation'
        for m in act: add(dep, uid, m, float(book[uid]))
    if a['cost']:
        for m in act:
            add(tax, uid, m, a['cost'] * TAX_RATE)
            if a['cls'] in REG_CLASSES: add(reg, uid, m, a['cost'] * REG_RATE)

# onsite diesel -> trucks/LD at the site by that month's miles
OS = pd.read_excel(U + 'a387c44d-Onsite_Fuel_Cost_353_356_359_Jan_Oct2026.xlsx', sheet_name='Monthly Cost', header=3).iloc[:10]
onsite_src = {}
for i, row in OS.iterrows():
    m = i + 1
    for site in ['353', '356', '359']:
        cost = float(row[f'{site} Cost']); onsite_src[(site, m)] = cost
        ids = [u for u, a in A.items() if a['store'] == site and a['cls'] in ('Truck', 'LD Vehicle') and u in mil and mil[u][m - 1] > 0]
        tot = sum(mil[u][m - 1] for u in ids)
        if tot > 0:
            for u in ids: add(onsite, u, m, cost * mil[u][m - 1] / tot)
        else:
            add_loc(site, 'onsite', m, cost)

# propane -> forklifts at location by hours (bottle fix x5 for 032/061/007; skip 122)
BOTTLE = {'32', '61', '7'}
prop_src = {}
for r in prop_raw.itertuples(index=False):
    s = sc(r.Location)
    if s == '122': continue
    for m, mn in zip(M, MN):
        c = float(getattr(r, mn)) * (5 if s in BOTTLE else 1)
        prop_src[(s, m)] = c
        fl = [u for u, a in A.items() if a['store'] == s and a['cls'] == 'Forklift' and m in a['active']]
        tot = sum(hrs[u][m - 1] for u in fl if u in hrs)
        if tot > 0:
            for u in fl:
                if u in hrs and hrs[u][m - 1] > 0: add(propane, u, m, c * hrs[u][m - 1] / tot)
        elif fl:
            for u in fl: add(propane, u, m, c / len(fl))
        else:
            add_loc(s, 'propane', m, c)

# pickup / cargo van standard maintenance rate (replaces recorded maintenance)
PICKUP_RATE = 0.14
maint_rec = {}
std_units = []
for uid, a in A.items():
    if a['cls'] == 'LD Vehicle' and str(a['type']).strip() in ('Pickup', 'Cargo Van', ''):
        a['pickup'] = str(a['type']).strip() != 'Cargo Van'
        a['std'] = True
        maint_rec[uid] = maint.get(uid, np.zeros(10)).copy()
        maint[uid] = mil.get(uid, np.zeros(10)) * PICKUP_RATE
        std_units.append(uid)
pk_rec = float(sum(v.sum() for v in maint_rec.values())); pk_std = float(sum(maint[u].sum() for u in std_units))

# ---------------------------------------------------------------- output
COMPS = ['maint', 'fuel_card', 'onsite', 'propane', 'dep', 'reg', 'tax']
G = dict(maint=maint, fuel_card=fcard, onsite=onsite, propane=propane, dep=dep, reg=reg, tax=tax)
def r2(x): return [round(float(v), 2) for v in x]
assets_out = []
for uid, a in A.items():
    rows = {c: G[c].get(uid, np.zeros(10)) for c in COMPS}
    mi = mil.get(uid, np.zeros(10)); hr = hrs.get(uid, np.zeros(10))
    if not a['active'] and not any(v.any() for v in rows.values()) and not mi.any():
        continue
    assets_out.append(dict(
        id=str(uid).replace('RENT:', ''), s=a['store'], c=a['cls'], t=a['type'], mk=a['make'], own=a['owned'], cost=a['cost'], cs=a['costsrc'],
        o=a['orig'], st=a['status'], r=a['roster'], fd=a.get('fully_dep', False),
        act=[1 if m in a['active'] else 0 for m in M],
        **{c: r2(rows[c]) for c in COMPS}, mi=r2(mi), hr=[round(float(v), 1) for v in hr],
        me=sorted(mil_est.get(uid, [])), pk=1 if a.get('pickup') else 0, std=1 if a.get('std') else 0,
        mrec=r2(maint_rec[uid]) if uid in maint_rec else None, he=(0 if uid in hours_actual_units else (1 if uid in hrs else 0))))
loc_out = [dict(s=s, comp=c, v=r2(v)) for (s, c), v in loc_level.items()]

# ---------------------------------------------------------------- notes / data issues
def fmt(v): return f'${v:,.0f}'
nr = [a for a in A.values() if not a['roster'] and not str(a['id']).startswith('RENT:')]
issues = []
issues.append(dict(cat='Assets', item='Units not on the 10/31 roster (disposed during 2026)', n=len(nr),
    detail='History kept in the months they had fuel, miles, spend or hours. Depreciation uses the March 2026 book amount; original cost for reg/tax implied from book depreciation × life.',
    list=', '.join(str(a['id']) for a in sorted(nr, key=lambda x: str(x['id']))[:400])))
nocost = [a for a in nr if not a['cost']]
issues.append(dict(cat='Assets', item='Disposed units with no book record (no depreciation / reg / tax)', n=len(nocost), detail='Only actual spend and fuel are carried.', list=', '.join(str(a['id']) for a in nocost)))
rnocost = R[(R['Asset Original Value'].isna()) | (R['Asset Original Value'] <= 0)]
issues.append(dict(cat='Assets', item='Roster units with no original value', n=len(rnocost), detail='No depreciation, registration or taxes calculated.', list=', '.join(map(str, rnocost['Asset Name']))))
issues.append(dict(cat='Assets', item='Fully depreciated owned units', n=sum(1 for a in A.values() if a.get('fully_dep')), detail='$0 depreciation; registration and taxes still charged on original cost.', list=''))
issues.append(dict(cat='Assets', item='Leased units', n=int((R['Asset Ownership'] != 'Company Owned').sum()), detail='No depreciation. Taxes/registration applied only where an original value exists.', list=''))
issues.append(dict(cat='Miles', item='Missing telematics months filled with neighbor-month average', n=len(filled_df),
    detail='Mainly May (Risk Management report) and July (Utilization report) dropped distribution vehicles. Estimated miles: ' +
    ', '.join(f"{MN[m-1]} {int(v):,}" for m, v in filled_df.groupby('Month').Miles.sum().items()), list=''))
issues.append(dict(cat='Miles', item='Sub / rental units with no unit number', n=int(rent.groupby(Mi['aid']).any().sum()),
    detail='Kept as their own rows at their store (mostly 359). They share onsite diesel by miles.', list=', '.join(sorted(Mi.loc[rent, 'Vehicle'].unique()))))
issues.append(dict(cat='Hours', item='Forklift / TMFL hours Jan–Aug are estimates', n=int(H.Unit.nunique()),
    detail='Estimated from each unit\'s lifetime average hrs/month; DVIR actuals start 8/24. Units with no actual readings: ' + str(sum(1 for a in assets_out if a['he'] == 1)), list=''))
chk = H.drop_duplicates('Unit'); chk = chk[chk['Check'].notna()]
issues.append(dict(cat='Hours', item='Hours flagged by the Check column (possible meter entry errors)', n=len(chk), detail='Used as provided — review these units before relying on their cost per hour.',
    list='; '.join(f"{u}: {c}" for u, c in zip(chk.Unit, chk.Check))))
nohrs = R[R['Asset Class'].isin(['Forklift', 'TMFL']) & ~R['Asset Name'].isin(H.Unit)]
issues.append(dict(cat='Hours', item='Roster forklifts/TMFLs with no hours', n=len(nohrs), detail='Costs included; no cost per hour.', list=', '.join(map(str, nohrs['Asset Name']))))
issues.append(dict(cat='Spend', item='Pickups & cargo vans: standard maintenance rate $0.14/mile', n=len(std_units),
    detail=f'Fexa captures little pickup spend (over half of pickups show none). Recorded maintenance of {fmt(pk_rec)} replaced by $0.14 × miles = {fmt(pk_std)} (160K-mile life, 3/4-ton gas, job-site use with occasional towing). Recorded spend still shown per unit on the Assets tab.', list=''))
issues.append(dict(cat='Spend', item='Multi-asset invoices split evenly across assets', n=int((SP.n_assets > 1).sum()),
    detail=f'Same invoice/work order total repeated on each asset; split removes {fmt(split_extra)} of double counting.', list=''))
issues.append(dict(cat='Spend', item='Non-fleet equipment spend excluded from cost per mile', n=len(nonfleet),
    detail=f'{fmt(nonfleet.amt.sum())} — insulation blowers, Holtec saw, ancillary materials, non-numeric asset IDs. Shown in totals as "Non-fleet".', list=', '.join(sorted(nonfleet['Asset Name'].astype(str).unique()))))
issues.append(dict(cat='Spend', item='Registration / tax invoices removed from maintenance', n=len(regtax_ex),
    detail=f'{fmt(regtax_ex.amt.sum())} removed to avoid double counting with calculated registration & taxes.', list=''))
issues.append(dict(cat='Fuel', item='Generic fuel cards (no unit number)', n=int(F.Unit.isna().sum()), detail=f'{fmt(F.loc[F.Unit.isna(), "Net Cost"].sum())} charged to the billed store, not to an asset.', list=''))
issues.append(dict(cat='Fuel', item='Onsite diesel Jan–Sep price is estimated', n=3, detail='Gallons exact from tank export; Jan–Sep $/gal implied, Oct from Sun Coast quotes. Allocated to trucks at 353/356/359 by monthly miles.', list=''))
issues.append(dict(cat='Fuel', item='Propane from 2027 forecast file used as 2026', n=int(len(prop_raw) - 1), detail='Gallons per location/month × plan rate; allocated to forklifts by hours. Palestine, Mt. Pleasant, Brownwood converted from bottle counts (×5 gal). Canyon Lake (122) excluded.', list=''))

# location assignment differences for roster units (informational)
recon = dict(
    maint_src=float(SP[amt].sum()), maint_split_removed=float(split_extra), maint_nonfleet=float(nonfleet.amt.sum()), maint_regtax=float(regtax_ex.amt.sum()),
    maint_assets=float(sum(v.sum() for v in maint.values())), pickup_recorded=pk_rec, pickup_std=pk_std,
    fuel_card_src=float(F['Net Cost'].sum()), fuel_card_out=float(sum(v.sum() for v in fcard.values()) + gen.sum()),
    onsite_src=float(sum(onsite_src.values())), onsite_out=float(sum(v.sum() for v in onsite.values()) + sum(v.sum() for (s, c), v in loc_level.items() if c == 'onsite')),
    propane_src=float(sum(prop_src.values())), propane_out=float(sum(v.sum() for v in propane.values()) + sum(v.sum() for (s, c), v in loc_level.items() if c == 'propane')),
    miles_src=float(Mi.Distance.sum()), miles_filled=float(filled_df.Miles.sum()), miles_out=float(sum(v.sum() for v in mil.values())),
    hours_src=float(H.Hours.sum()), hours_out=float(sum(v.sum() for v in hrs.values())),
    dep_out=float(sum(v.sum() for v in dep.values())), reg_out=float(sum(v.sum() for v in reg.values())), tax_out=float(sum(v.sum() for v in tax.values())),
)
nf = nonfleet.groupby(['store', 'Month']).amt.sum()
nonfleet_out = {}
for (s, m), v in nf.items():
    ensure_store(s); nonfleet_out.setdefault(s, [0] * 10)[m - 1] = round(float(v), 2)

used = {a['s'] for a in assets_out} | {r['s'] for r in loc_out} | set(nonfleet_out)
stores = {k: v for k, v in stores.items() if k in used}
out = dict(months=MN, stores=stores, assets=assets_out, loc=loc_out, nonfleet=nonfleet_out, issues=issues, recon=recon,
           built='2026-11-08', rates=dict(tax=TAX_RATE, reg=REG_RATE))
json.dump(out, open('data.json', 'w'), separators=(',', ':'), default=lambda o: None if (isinstance(o, float) and np.isnan(o)) else str(o))
print(json.dumps(recon, indent=1))
print('assets', len(assets_out), 'loc rows', len(loc_out), 'stores', len(stores))
