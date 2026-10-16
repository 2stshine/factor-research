"""Past-only market/friction measurements, vector and independent scalar oracles.

The market is the lag-cap-weighted certified KRX common-stock PRICE universe,
not an official total-return index or an excess-return benchmark. This is an
explicit domestic adaptation. No future strategy labels enter any calculation.
"""
import warnings
import numpy as np
import pandas as pd

def moments(y,x):
    x=np.broadcast_to(x,y.shape)
    valid=np.isfinite(y)&np.isfinite(x)
    n=valid.sum(axis=0)
    with warnings.catch_warnings(),np.errstate(all='ignore'):
        warnings.simplefilter('ignore',RuntimeWarning)
        yy=np.where(valid,y,np.nan);xx=np.where(valid,x,np.nan)
        a=yy-np.nanmean(yy,axis=0);b=xx-np.nanmean(xx,axis=0)
        sxx=np.nansum(b*b,axis=0);syy=np.nansum(a*a,axis=0);sxy=np.nansum(a*b,axis=0)
        beta=sxy/np.where(sxx>1e-16,sxx,np.nan)
        residual=a-beta*b
    return n,a,b,sxx,syy,sxy,beta,residual

def market_series(x):
    ret=x['returns'];cap=x['market_cap']
    weight=np.vstack([np.full((1,cap.shape[1]),np.nan),cap[:-1]])
    valid=np.isfinite(ret)&np.isfinite(weight)&(weight>0)
    denominator=np.where(valid,weight,0).sum(axis=1)
    with np.errstate(all='ignore'):
        result=np.where(valid,weight*ret,0).sum(axis=1)/denominator
    result[valid.sum(axis=1)<100]=np.nan
    return result

def edge_vector(o,h,l,c):
    """Vectorized EDGE equations; all columns use the same regular time grid."""
    o,h,l,c=(np.log(v) for v in [o,h,l,c]);mid=(h+l)/2
    hp,lp,cp,mp=h[:-1],l[:-1],c[:-1],mid[:-1]
    o,h,l,c,mid=o[1:],h[1:],l[1:],c[1:],mid[1:]
    r1,r2,r3,r4,r5=mid-o,o-mp,mid-cp,cp-mp,o-cp
    tau=np.where(np.isfinite(h)&np.isfinite(l)&np.isfinite(cp),((h!=l)|(l!=cp)).astype(float),np.nan)
    po1=tau*np.where(np.isfinite(o)&np.isfinite(h),o!=h,np.nan)
    po2=tau*np.where(np.isfinite(o)&np.isfinite(l),o!=l,np.nan)
    pc1=tau*np.where(np.isfinite(cp)&np.isfinite(hp),cp!=hp,np.nan)
    pc2=tau*np.where(np.isfinite(cp)&np.isfinite(lp),cp!=lp,np.nan)
    with warnings.catch_warnings(),np.errstate(all='ignore'):
        warnings.simplefilter('ignore',RuntimeWarning)
        mean=lambda a:np.nanmean(a,axis=0)
        pt=mean(tau);po=mean(po1)+mean(po2);pc=mean(pc1)+mean(pc2)
        u=r1-mean(r1)/pt*tau;v=r3-mean(r3)/pt*tau;w=r5-mean(r5)/pt*tau
        a=-4*u*r2/po-4*v*r4/pc;b=-4*u*r5/po-4*w*r4/pc
        ea,eb=mean(a),mean(b)
        va,vb=mean(a*a)-ea*ea,mean(b*b)-eb*eb
        spread2=np.where(va+vb>0,(vb*ea+va*eb)/(va+vb),(ea+eb)/2)
        result=np.sqrt(np.maximum(spread2,0))
        result[(np.nansum(tau,axis=0)<2)|(po<=0)|(pc<=0)]=np.nan
    return result

def edge_scalar(open,high,low,close):
    """Independent scalar transcription of reviewed author implementation.

    Derived from eguidotti/bidask, commit 1caba55d63ebab6c855536be51c43bdfc48d2dec.
    Copyright (c) 2024 Emanuele Guidotti, MIT; see docs/reference-edge-third-party-notice.md.
    Signed estimate is clipped to zero, as recommended for regression studies.
    """
    if len(open)<3:return np.nan
    with warnings.catch_warnings(),np.errstate(all='ignore'):
        warnings.simplefilter('ignore',RuntimeWarning)
        o,h,l,c=[np.log(np.asarray(v)) for v in [open,high,low,close]]
        m=(h+l)/2
        h1,l1,c1,m1=h[:-1],l[:-1],c[:-1],m[:-1]
        o,h,l,c,m=o[1:],h[1:],l[1:],c[1:],m[1:]
        r1,r2,r3,r4,r5=m-o,o-m1,m-c1,c1-m1,o-c1
        tau=np.where(np.isnan(h)|np.isnan(l)|np.isnan(c1),np.nan,(h!=l)|(l!=c1))
        po1=tau*np.where(np.isnan(o)|np.isnan(h),np.nan,o!=h)
        po2=tau*np.where(np.isnan(o)|np.isnan(l),np.nan,o!=l)
        pc1=tau*np.where(np.isnan(c1)|np.isnan(h1),np.nan,c1!=h1)
        pc2=tau*np.where(np.isnan(c1)|np.isnan(l1),np.nan,c1!=l1)
        pt=np.nanmean(tau);po=np.nanmean(po1)+np.nanmean(po2);pc=np.nanmean(pc1)+np.nanmean(pc2)
        if np.nansum(tau)<2 or po==0 or pc==0:return np.nan
        d1=r1-np.nanmean(r1)/pt*tau;d3=r3-np.nanmean(r3)/pt*tau;d5=r5-np.nanmean(r5)/pt*tau
        x1=-4/po*d1*r2+-4/pc*d3*r4;x2=-4/po*d1*r5+-4/pc*d5*r4
        e1,e2=np.nanmean(x1),np.nanmean(x2)
        v1=np.nanmean(x1*x1)-e1*e1;v2=np.nanmean(x2*x2)-e2*e2
        s2=(v2*e1+v1*e2)/(v1+v2) if v1+v2>0 else (e1+e2)/2
        return np.sqrt(max(s2,0))

def _ols_residual(y,m):
    valid=np.isfinite(y)&np.isfinite(m)
    y,m=y[valid],m[valid]
    if len(y)<3 or np.var(m)*len(m)<=1e-16:return None
    X=np.column_stack([np.ones(len(m)),m])
    beta=np.linalg.lstsq(X,y,rcond=None)[0]
    return y,m,y-X@beta,beta

def monthly_risk(x,dates,end,market,*,oracle=False):
    """One month of measurements, all assets. Oracle regresses stock by stock."""
    ret=x['returns'];nassets=ret.shape[1]
    lo=max(0,end-251);yy=ret[lo:end+1];mm=market[lo:end+1,None]
    month=np.flatnonzero(dates.to_period('M')==dates[end].to_period('M'))
    month=month[month<=end];mlo=int(month[0]);short=ret[mlo:end+1];short_m=market[mlo:end+1,None]
    result={k:np.full(nassets,np.nan) for k in ['downside_beta','idiosyncratic_volatility','coskewness','cokurtosis','return_autocorrelation','liquidity_reversal','edge_spread','bab_beta']}
    logs=x.get('log_returns')
    if logs is None:logs=np.log1p(ret)
    mlog=np.log1p(market)
    three=x.get('log_returns_3')
    if three is None:three=logs+np.vstack([np.full((1,nassets),np.nan),logs[:-1]])+np.vstack([np.full((2,nassets),np.nan),logs[:-2]])
    mthree=mlog+np.r_[np.nan,mlog[:-1]]+np.r_[np.nan,np.nan,mlog[:-2]]
    clo=max(0,end-1259)
    if oracle:
        for a in range(nassets):
            fitted=_ols_residual(yy[:,a],mm[:,0])
            if fitted is not None:
                y,m,res,b=fitted
                if len(y)>=200:
                    result['idiosyncratic_volatility'][a]=np.std(res,ddof=1)
                    center=m-m.mean();den=np.sqrt(np.mean(res*res))*np.mean(center*center)**1.5
                    if den>1e-16:result['cokurtosis'][a]=np.mean(res*center**3)/den
            down=market[lo:end+1]<np.nanmean(market[lo:end+1])
            fitted=_ols_residual(yy[down,a],market[lo:end+1][down])
            if fitted is not None and len(fitted[0])>=60 and np.isfinite(yy[:,a]).sum()>=200:
                result['downside_beta'][a]=fitted[3][1]
            fitted=_ols_residual(short[:,a],short_m[:,0])
            if fitted is not None and len(fitted[0])>=15:
                y,m,res,_=fitted;center=m-m.mean();den=np.sqrt(np.mean(res*res))*np.mean(center*center)
                if den>1e-16:result['coskewness'][a]=np.mean(res*center**2)/den
            r1=ret[mlo:end+1,a];r0=ret[max(0,mlo-1):end,a]
            if len(r1)==len(r0):
                ok=np.isfinite(r1)&np.isfinite(r0)
                if ok.sum()>=15 and np.var(r1[ok])*ok.sum()>1e-16 and np.var(r0[ok])*ok.sum()>1e-16:
                    result['return_autocorrelation'][a]=np.corrcoef(r1[ok],r0[ok])[0,1]
            rhs=np.column_stack([np.ones(len(month)-1),ret[mlo:end,a],np.sign(ret[mlo:end,a]-market[mlo:end])*x['trading_value'][mlo:end,a]/1e9])
            lhs=ret[mlo+1:end+1,a]-market[mlo+1:end+1]
            ok=np.isfinite(rhs).all(axis=1)&np.isfinite(lhs)
            centered=rhs[ok,1:]-rhs[ok,1:].mean(axis=0) if ok.any() else np.zeros((0,2))
            determinant=np.linalg.det(centered.T@centered)
            if ok.sum()>=15 and determinant>1e-16 and np.linalg.matrix_rank(rhs[ok])==3:
                result['liquidity_reversal'][a]=np.linalg.lstsq(rhs[ok],lhs[ok],rcond=None)[0][2]
            o,h,l,c=[x[k][mlo:end+1,a] for k in ['open','high','low','close']]
            if np.isfinite(o).sum()>=15:result['edge_spread'][a]=edge_scalar(o,h,l,c)
            r=three[clo:end+1,a];m=mthree[clo:end+1];ok=np.isfinite(r)&np.isfinite(m)
            v=logs[lo:end+1,a];vm=mlog[lo:end+1];okv=np.isfinite(v)&np.isfinite(vm)
            if ok.sum()>=750 and okv.sum()>=120 and np.std(r[ok])>1e-8 and np.std(m[ok])>1e-8 and np.std(vm[okv])>1e-8:
                beta=np.corrcoef(r[ok],m[ok])[0,1]*np.std(v[okv],ddof=1)/np.std(vm[okv],ddof=1)
                result['bab_beta'][a]=.6*beta+.4
        return result
    with warnings.catch_warnings(),np.errstate(all='ignore'):
        warnings.simplefilter('ignore',RuntimeWarning)
        n,a,b,sxx,syy,sxy,beta,res=moments(yy,mm)
        result['idiosyncratic_volatility']=np.where(n>=200,np.sqrt(np.nansum(res*res,axis=0)/(n-1)),np.nan)
        den=np.sqrt(np.nanmean(res*res,axis=0))*np.nanmean(b*b,axis=0)**1.5
        result['cokurtosis']=np.where((n>=200)&(den>1e-16),np.nanmean(res*b**3,axis=0)/den,np.nan)
        down=mm[:,0]<np.nanmean(mm)
        nd,*_,bd,_rd=moments(yy[down],mm[down])
        result['downside_beta']=np.where((nd>=60)&(n>=200),bd,np.nan)
        ns,a,b,xx,yy2,xy,bs,rs=moments(short,short_m)
        den=np.sqrt(np.nanmean(rs*rs,axis=0))*np.nanmean(b*b,axis=0)
        result['coskewness']=np.where((ns>=15)&(den>1e-16),np.nanmean(rs*b*b,axis=0)/den,np.nan)
        if mlo>0:
            na,a,b,xx,yy2,xy,_,_=moments(ret[mlo:end+1],ret[mlo-1:end])
            result['return_autocorrelation']=np.where((na>=15)&(xx>1e-16)&(yy2>1e-16),xy/np.sqrt(xx*yy2),np.nan)
        r1=ret[mlo:end];r2=np.sign(r1-market[mlo:end,None])*x['trading_value'][mlo:end]/1e9
        target=ret[mlo+1:end+1]-market[mlo+1:end+1,None]
        ok=np.isfinite(r1)&np.isfinite(r2)&np.isfinite(target)
        u,v,y=(np.where(ok,z,np.nan) for z in [r1,r2,target])
        u=u-np.nanmean(u,axis=0);v=v-np.nanmean(v,axis=0);y=y-np.nanmean(y,axis=0)
        uu,vv,uv,uy,vy=(np.nansum(z,axis=0) for z in [u*u,v*v,u*v,u*y,v*y])
        determinant=uu*vv-uv*uv
        result['liquidity_reversal']=np.where((ok.sum(axis=0)>=15)&(determinant>1e-16),(uu*vy-uv*uy)/determinant,np.nan)
        result['edge_spread']=edge_vector(*(x[k][mlo:end+1] for k in ['open','high','low','close']))
        result['edge_spread'][np.isfinite(x['open'][mlo:end+1]).sum(axis=0)<15]=np.nan
        nc,a,b,xx,yy2,xy,_,_=moments(three[clo:end+1],mthree[clo:end+1,None])
        nv,a,b,vxx,vyy,_,_,_=moments(logs[lo:end+1],mlog[lo:end+1,None])
        estimate=xy/np.sqrt(xx*yy2)*np.sqrt(vyy/vxx)
        result['bab_beta']=np.where((nc>=750)&(nv>=120)&(xx>1e-16)&(yy2>1e-16)&(vxx>1e-16),.6*estimate+.4,np.nan)
    return result

def price_delay(weekly,weekly_market,end_date,oracle=False):
    market=weekly_market
    design=pd.concat([market.shift(i).rename(str(i)) for i in range(5)],axis=1)
    design=design.loc[design.index<=end_date].tail(52)
    ys=weekly.reindex(design.index)
    result=np.full(ys.shape[1],np.nan)
    for a in range(ys.shape[1]):
        y=ys.iloc[:,a].to_numpy();x=design.to_numpy()
        ok=np.isfinite(y)&np.isfinite(x).all(axis=1)
        if ok.sum()<40:continue
        y=y[ok];x=x[ok];full=np.column_stack([np.ones(len(y)),x]);small=full[:,:2]
        if np.linalg.matrix_rank(full)<6:continue
        variance=np.sum((y-y.mean())**2)
        if variance<=1e-16:continue
        if oracle:
            rsmall=y-small@np.linalg.lstsq(small,y,rcond=None)[0]
            rfull=y-full@np.linalg.lstsq(full,y,rcond=None)[0]
        else:
            rsmall=y-small@np.linalg.solve(small.T@small,small.T@y)
            rfull=y-full@np.linalg.solve(full.T@full,full.T@y)
        r2small=1-np.dot(rsmall,rsmall)/variance;r2full=1-np.dot(rfull,rfull)/variance
        if r2full>1e-10:result[a]=1-r2small/r2full
    return result

def volume_trend(volumes,index,oracle=False):
    values=volumes[max(0,index-59):index+1]
    time=np.arange(len(values),dtype=float)
    if oracle:
        result=np.full(values.shape[1],np.nan)
        for a in range(values.shape[1]):
            y=values[:,a];ok=np.isfinite(y)
            if ok.sum()<30 or y[ok].mean()<=0:continue
            coef=np.linalg.lstsq(np.column_stack([np.ones(ok.sum()),time[ok]]),y[ok],rcond=None)[0]
            result[a]=coef[1]/y[ok].mean()
        return result
    n,y,t,xx,yy,xy,beta,res=moments(values,time[:,None])
    with warnings.catch_warnings(),np.errstate(all='ignore'):
        warnings.simplefilter('ignore',RuntimeWarning)
        mean=np.nanmean(values,axis=0)
        return np.where((n>=30)&(mean>0),beta/mean,np.nan)
