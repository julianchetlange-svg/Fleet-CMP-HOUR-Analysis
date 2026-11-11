import base64, json
t=open('template.html').read()
logo='data:image/png;base64,'+base64.b64encode(open('/mnt/user-data/uploads/abca4f5e-image.png','rb').read()).decode()
d=json.load(open('data.json'))
rows=json.load(open('proposal.json'))
cpm_rank={}
ranked=sorted({a['s'] for a in d['assets'] if a.get('pk')==1 and a['c']=='LD Vehicle' and a['s'].isdigit() and 1<=int(a['s'])<=121})
for r in rows: pass
d['proposal']=dict(rate=995.46,new_truck=55000,rows=rows,assume=[
 'The 11 donor stores rank in the bottom 15 for pickup miles <b>and</b> the top 15 for all-in cost per mile (Jan–Oct 2026).',
 'Store P&amp;L savings use the flat pickup billing of $995.46 per store per month (annualized ×12). Actual expense removed is Jan–Oct depreciation, standard maintenance ($0.14/mi), registration and taxes, annualized.',
 'Fuel is assumed to stay: deliveries and pickups move to another vehicle at the store, so fuel spend is not counted as savings.',
 'Company-level, the redeployed trucks keep depreciating at the receiving stores; the real company savings are the CAPEX avoided and the depreciation of new trucks that are not bought.',
 'Each placement avoids one $55,000 delivered replacement pickup. Disposal proceeds from the replaced trucks are not included.',
 'Placement: newest trucks (most depreciation life left) go to the highest-usage receiving stores; Canyon Lake receives a late-2023 truck. Millwork (450) is assumed to replace its highest-mileage pickup, 599007.',
 'The three 2022 trucks (Bryan, Odessa, Richwood) reach 60 months in Apr–Jun 2027, so they are best suited to the lowest-usage receiving stores and may need replacing sooner than the 2023–2024 units.'])
data=json.dumps(d,separators=(',',':')).replace('</','<\\/')
out=t.replace('__LOGO__',logo).replace('__DATA__',data)
open('/home/claude/work/McCoys_Fleet_CPM_YTD_2026.html','w').write(out)
print(len(out))
