import base64, json
t=open('template.html').read()
logo='data:image/png;base64,'+base64.b64encode(open('/mnt/user-data/uploads/abca4f5e-image.png','rb').read()).decode()
d=json.load(open('data.json'))
data=json.dumps(d,separators=(',',':')).replace('</','<\\/')
out=t.replace('__LOGO__',logo).replace('__DATA__',data)
open('/home/claude/work/McCoys_Fleet_CPM_YTD_2026.html','w').write(out)
print(len(out))
