import json
d=json.load(open('data.json')); A={a['id']:a for a in d['assets']}
DON=['601031','601030','601036','601037','601048','601039','601025','601008','600008','600005','600001']  # newest first
REC=[('450','599007'),('52','599003'),('63','598008'),('8','596007'),('117','599030'),('67','600006'),('122',None),('18','596002'),('53','599025'),('70','597002'),('90','594179')]
RATE=995.46
def ann(a,keys): return sum(sum(a[k]) for k in keys)/10*12
rows=[]
for u,(rs,ru) in zip(DON,REC):
    a=A[u]; y,m=int(a['o'][:4]),int(a['o'][5:7]); el=(2026-y)*12+(10-m)+1
    nbv=max(0,a['cost']-a['cost']/60*el); rem=max(0,60-el)
    r=A[ru] if ru else None
    rows.append(dict(store=a['s'],name=d['stores'][a['s']]['name'],unit=u,orig=a['o'],cost=a['cost'],mi=sum(a['mi']),annmi=sum(a['mi'])*1.2,
      cpm=sum(sum(a[k]) for k in ['maint','fuel_card','dep','reg','tax'])/sum(a['mi']),
      ex=ann(a,['maint','dep','reg','tax']),fuel=ann(a,['fuel_card']),nbv=nbv,rem=rem,
      to=rs,toname=d['stores'].get(rs,{}).get('name','Canyon Lake (new store)'),repl=ru,repl_o=r['o'] if r else '',repl_mi=sum(r['mi'])*1.2 if r else None))
for r in rows: print(r['store'],r['name'],r['unit'],r['orig'][:7],round(r['cost']),round(r['annmi']),round(r['cpm'],2),round(r['ex']),round(r['fuel']),round(r['nbv']),r['rem'],'->',r['to'],r['toname'],r['repl'],r['repl_o'][:7],round(r['repl_mi'] or 0))
print('billing',RATE*12*11,'actual ex fuel',round(sum(r['ex'] for r in rows)),'fuel',round(sum(r['fuel'] for r in rows)),'nbv',round(sum(r['nbv'] for r in rows)),'capex',55000*11,'dep avoided',55000/5*11)
json.dump(rows,open('proposal.json','w'))
