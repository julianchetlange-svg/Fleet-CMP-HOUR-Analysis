import pandas as pd, re
U='/mnt/user-data/uploads/'
R=pd.read_excel(U+'c06aef92-Current_Assets_10_31_2026.xlsx'); R['Asset Class']=R['Asset Class'].str.strip()
FUEL={1:'2fb350ae-Company_Fuel_Jan_2026',2:'dd920b6c-Company_Fuel_Feb',3:'1ecffa0b-March_Company_Fuel',
      4:'5a70c13f-April_Fuel_Transactions',5:'7780d629-May_2026_Fuel_Card_Transaciotns_WEX',6:'b1007def-Fuel_Transactions_June_2026',
      7:'5a784177-Wex_Download_July',8:'69bfb840-August_Fuel',9:'02c1ce52-September_Fuel_2026',10:'0e885de4-October_Fuel_2026'}
MILES={1:'28de5200-Miles_Driven_Jan',2:'ba59d459-February_Miles',3:'00ed060c-Miles_March',
       4:'704f7693-April_Miles',5:'bade9c84-May_Miles_Geotab',6:'700f9df8-June_Company_Miles_by_Asset_June',
       7:'76baf658-Miles_Driven_July',8:'48fa3063-August_Miles_Driven',9:'168a90c3-Miles_September_2026',10:'6642bda1-October_Miles'}
def _fuel_sheet(p):
    x=pd.ExcelFile(U+p+'.xlsx')
    for s in x.sheet_names:
        d=x.parse(s)
        if 'Transaction Date' in d.columns: return d
    raise ValueError(p)
def fuel():
    out=[]
    for m,p in FUEL.items():
        f=_fuel_sheet(p); f['Month']=m; out.append(f)
    f=pd.concat(out,ignore_index=True)
    f['Unit']=pd.to_numeric(f['Custom Vehicle/Asset ID'],errors='coerce')
    return f
def miles():
    out=[]
    for m,p in MILES.items():
        d=pd.read_excel(U+p+'.xlsx',sheet_name='Report'); d.columns=[c.strip() for c in d.columns]
        d=d.rename(columns={'Asset':'Vehicle','Distance driven':'Distance'})
        v=d['Vehicle'].astype(str)
        d['Sold']=v.str.contains('sold',case=False)
        d['Store']=v.str.replace(r'^(?i:sold)-','',regex=True).str.split('-').str[0].str.lstrip('0')
        d=d[['Store','Vehicle','Distance','Sold']].copy(); d['Month']=m; d['src']=p; out.append(d)
    d=pd.concat(out,ignore_index=True)
    d['Unit']=pd.to_numeric(d['Vehicle'].astype(str).str.extract(r'(?:^|-)(\d{5,6})(?:-|$)')[0],errors='coerce')
    return d
HOURS='44f51cc8-mccoys_monthly_hours_2026'
MON=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct']
def hours():
    out=[]
    for s,fleet in [('Store Forklifts','Store Forklift'),('Distribution Forklifts','Distribution Forklift'),('TMFLs','TMFL')]:
        d=pd.read_excel(U+HOURS+'.xlsx',sheet_name=s,header=3)
        d=d[pd.to_numeric(d['Asset #'],errors='coerce').notna()].copy()
        d['Unit']=d['Asset #'].astype(int); d['Fleet']=fleet
        l=d.melt(id_vars=['Unit','Fleet','Location','Months Actual','Check'],value_vars=MON,var_name='Mon',value_name='Hours')
        l['Month']=l.Mon.map({m:i+1 for i,m in enumerate(MON)})
        l['Hours']=pd.to_numeric(l.Hours,errors='coerce').fillna(0)
        out.append(l.drop(columns='Mon'))
    return pd.concat(out,ignore_index=True)
