import sys; sys.path.insert(0,'.')
from load import *
import numpy as np
def clean_odo(f, unit):
    x=f[f.Unit==unit].sort_values('Transaction Date')
    v=x['Current Odometer'].astype(float).values; d=x['Transaction Date'].values
    keep=[(dd,o) for dd,o in zip(d,v) if 1000<o<500000 and str(unit) not in str(int(o)) and abs(o-unit)>5]
    if len(keep)<4: return None, None
    vals=np.array([o for _,o in keep[-20:]]); med=np.median(vals[-8:])
    good=[(dd,o) for dd,o in keep[-20:] if abs(o-med)<max(0.2*med,3000)]
    if len(good)<4: return None, None
    # must be roughly monotonic: take the last reading that is >= the running median of the prior good readings
    g=[o for _,o in good[-6:]]
    if (max(g)-min(g))>max(0.25*np.median(g),4000): return None, None
    o=max(g)
    return float(o), str(pd.Timestamp(good[-1][0]).date())
if __name__=='__main__':
    f=fuel()
    for u in [601031,601030,601036,601037,601048,601039,601025,601008,600008,600005,600001,599007,599003,598008,596007,599030,600006,596002,599025,597002,594179]:
        print(u, clean_odo(f,u))
