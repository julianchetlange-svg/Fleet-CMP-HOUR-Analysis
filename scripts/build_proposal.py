import base64, json
t=open('proposal_template.html').read()
logo='data:image/png;base64,'+base64.b64encode(open('/mnt/user-data/uploads/abca4f5e-image.png','rb').read()).decode()
data=json.dumps(json.load(open('proposal.json')),separators=(',',':')).replace('</','<\\/')
open('McCoys_Pickup_Reallocation_2027.html','w').write(t.replace('__LOGO__',logo).replace('__DATA__',data))
