"""Selected publicly documented WorldQuant formulas, with two interpreters.

Daily cross-sectional ranks are never replaced by monthly ranks. Returns are
price-only. Raw OHLCV windows crossing a price-adjustment-factor change must be
excluded by the capture adapter. These are monthly sampled short-horizon
measurements, not reproduced original portfolio returns.
"""
import ast
import operator
import warnings
import numpy as np
import pandas as pd
from scipy.stats import rankdata

FORMULAS={
 1:'rank(argmax(where(returns<0,std(returns,20),close)**2,5))-0.5',
 2:'-corr(rank(delta(log(volume),2)),rank((close-open)/open),6)',
 3:'-corr(rank(open),rank(volume),10)',
4:'-tsrank(rank(low),9)',
 5:'rank(open-mean(vwap,10))*(-abs(rank(close-vwap)))',
 6:'-corr(open,volume,10)',
 8:'-rank(delta(sum(open,5)*sum(returns,5),10))',
9:'where((minimum(delta(close,1),5)>0)|(maximum(delta(close,1),5)<0),delta(close,1),-delta(close,1))',
 11:'(rank(maximum(vwap-close,3))+rank(minimum(vwap-close,3)))*rank(delta(volume,3))',
 12:'sign(delta(volume,1))*(-delta(close,1))',
 13:'-rank(cov(rank(close),rank(volume),5))',
 14:'-rank(delta(returns,3))*corr(open,volume,10)',
 15:'-sum(rank(corr(rank(high),rank(volume),3)),3)',
 18:'-rank(std(abs(close-open),5)+(close-open)+corr(close,open,10))',
 19:'-sign((close-delay(close,7))+delta(close,7))*(1+rank(1+sum(returns,250)))',
 20:'-rank(open-delay(high,1))*rank(open-delay(close,1))*rank(open-delay(low,1))',
 22:'-delta(corr(high,volume,5),5)*rank(std(close,20))',
 23:'where(mean(high,20)<high,-delta(high,2),0)',
 24:'where(delta(mean(close,100),100)/delay(close,100)<=0.05,-(close-minimum(close,100)),-delta(close,3))',
 26:'-maximum(corr(tsrank(volume,5),tsrank(high,5),5),3)',
 30:'(1-rank(sign(delta(close,1))+sign(delay(close,1)-delay(close,2))+sign(delay(close,2)-delay(close,3))))*sum(volume,5)/sum(volume,20)',
 34:'rank(1-rank(std(returns,2)/std(returns,5))+1-rank(delta(close,1)))',
 35:'tsrank(volume,32)*(1-tsrank(close+high-low,16))*(1-tsrank(returns,32))',
 37:'rank(corr(delay(open-close,1),close,200))+rank(open-close)',
38:'-rank(tsrank(close,10))*rank(close/open)',
 41:'(high*low)**0.5-vwap',
 44:'-corr(high,rank(volume),5)',
 52:'(-minimum(low,5)+delay(minimum(low,5),5))*rank((sum(returns,240)-sum(returns,20))/220)*tsrank(volume,5)',
 55:'-corr(rank((close-minimum(low,12))/(maximum(high,12)-minimum(low,12))),rank(volume),6)',
 60:'-(2*scale(rank(((close-low)-(high-close))/(high-low)*volume))-scale(rank(argmax(close,10))))',
 101:'(close-open)/(high-low+0.001)',
}

NAMES={1:'하락 변동성과 고점 시점',2:'거래량 변화와 장중수익 순위 관계',3:'시가·거래량 순위의 동행성',
4:'저가 순위의 단기 위치',6:'시가와 거래량의 상관',8:'가격수준 가중 단기 추세 변화',9:'추세 연속성에 따른 반전',
12:'거래량 방향 조건부 가격변화',13:'가격·거래량 순위 공분산',14:'수익률 가속과 거래량 관계',
15:'고가·거래량 상관 순위의 누적',18:'장중 가격폭과 시가·종가 동행',19:'장단기 방향의 결합',
20:'전일 가격범위 대비 시가 갭',22:'고가·거래량 관계 변화와 가격 변동',23:'평균 고가 돌파 조건부 반전',
24:'장기추세 조건부 단기 반전',26:'거래량·고가 시계열 순위 관계',30:'가격방향 일관성과 거래집중',
34:'단기 변동성 비율과 반전',35:'거래량·가격범위·수익률의 위치',37:'장중 압력의 지연 상관',
38:'가격 시계열 위치와 시가 대비 종가',44:'고가와 거래량 순위 상관',52:'저점 이동과 중기 추세의 거래량 조건',
55:'가격범위 위치와 거래량 순위 관계',60:'거래량 가중 가격위치와 고점 시점',101:'일중 범위로 조정한 몸통 크기'}
NAMES.update({5:'평균 체결가격 대비 시가·종가 괴리',11:'체결가격 괴리 범위와 거래량 변화',41:'고저가 중심과 평균 체결가격 괴리'})

OPS={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv,
     ast.Pow:operator.pow,ast.BitOr:lambda a,b:np.where(np.isfinite(a)&np.isfinite(b),np.logical_or(a,b),np.nan)}
CMP={ast.Lt:operator.lt,ast.LtE:operator.le,ast.Gt:operator.gt,ast.GtE:operator.ge}

def numpy_rolling(x,n,op,y=None):
    """Independent centered-window oracle; bounded working memory per 24 stocks."""
    result=np.full(x.shape,np.nan)
    if len(x)<n:return result
    for first in range(0,x.shape[1],24):
        last=min(x.shape[1],first+24)
        windows=np.lib.stride_tricks.sliding_window_view(x[:,first:last],n,axis=0)
        complete=np.isfinite(windows).all(axis=-1)
        with warnings.catch_warnings(),np.errstate(all='ignore'):
            warnings.simplefilter('ignore',RuntimeWarning)
            if op in ('mean','sum','min','max','std'):
                fn={'mean':np.mean,'sum':np.sum,'min':np.min,'max':np.max,'std':lambda a,axis:np.std(a,axis=axis,ddof=1)}[op]
                value=fn(windows,axis=-1)
            elif op=='rank':
                end=windows[:,:,-1,None]
                value=((windows<end).sum(axis=-1)+((windows==end).sum(axis=-1)+1)/2)/n
            elif op=='argmax':value=np.argmax(windows,axis=-1)+1
            else:
                others=np.lib.stride_tricks.sliding_window_view(y[:,first:last],n,axis=0)
                complete &= np.isfinite(others).all(axis=-1)
                a=windows-windows.mean(axis=-1,keepdims=True)
                b=others-others.mean(axis=-1,keepdims=True)
                covariance=(a*b).sum(axis=-1)/(n-1)
                if op=='cov':value=covariance
                else:
                    denominator=np.sqrt((a*a).sum(axis=-1)*(b*b).sum(axis=-1))
                    value=(a*b).sum(axis=-1)/denominator
                    value=np.clip(value,-1,1)
                    complete &= (np.ptp(windows,axis=-1)>1e-12*np.maximum(1,np.max(abs(windows),axis=-1)))
                    complete &= (np.ptp(others,axis=-1)>1e-12*np.maximum(1,np.max(abs(others),axis=-1)))
            result[n-1:,first:last]=np.where(complete,value,np.nan)
    return result

def evaluate(formula,inputs,backend='pandas'):
    if backend not in {'pandas','numpy'}:raise ValueError('Unknown interpreter')
    def roll(x,n,op,y=None):
        n=int(n)
        if backend=='numpy':return numpy_rolling(x,n,op,y)
        f=pd.DataFrame(x);window=f.rolling(n,min_periods=n)
        if op in {'mean','sum','min','max','std'}:result=getattr(window,op)()
        elif op=='rank':result=window.rank(method='average',pct=True)
        elif op=='argmax':result=window.apply(lambda v:np.argmax(v)+1,raw=True)
        elif op=='cov':result=window.cov(pd.DataFrame(y))
        else:
            other=pd.DataFrame(y).rolling(n,min_periods=n)
            result=window.corr(pd.DataFrame(y)).clip(-1,1)
            result=result.where((window.max()-window.min())>1e-12*window.max().abs().clip(lower=1))
            result=result.where((other.max()-other.min())>1e-12*other.max().abs().clip(lower=1))
        return result.to_numpy()
    def shift(x,n):
        n=int(n);out=np.full(x.shape,np.nan)
        if n==0:return x.copy()
        out[n:]=x[:-n];return out
    def rank(x):
        # Published operators leave numerical ties unspecified. Freeze a
        # 12-decimal tie convention rather than rank floating roundoff noise.
        x=np.where(np.isfinite(x),np.round(x,12),np.nan)
        if backend=='pandas':return pd.DataFrame(x).rank(axis=1,method='average',pct=True).to_numpy()
        return rankdata(x,axis=1,method='average',nan_policy='omit')/np.isfinite(x).sum(axis=1)[:,None]
    funcs={'rank':rank,'delay':shift,'delta':lambda x,n:x-shift(x,n),'log':np.log,'abs':np.abs,'sign':np.sign,
           'scale':lambda x:x/np.nansum(abs(x),axis=1)[:,None],
           'where':lambda c,a,b:np.where(np.isfinite(c),np.where(c,a,b),np.nan),
           'mean':lambda x,n:roll(x,n,'mean'),'sum':lambda x,n:roll(x,n,'sum'),
           'std':lambda x,n:roll(x,n,'std'),'minimum':lambda x,n:roll(x,n,'min'),
           'maximum':lambda x,n:roll(x,n,'max'),'argmax':lambda x,n:roll(x,n,'argmax'),
           'tsrank':lambda x,n:roll(x,n,'rank'),'corr':lambda x,y,n:roll(x,n,'corr',y),
           'cov':lambda x,y,n:roll(x,n,'cov',y)}
    def visit(node):
        if isinstance(node,ast.Expression):return visit(node.body)
        if isinstance(node,ast.Constant) and isinstance(node.value,(int,float)):return node.value
        if isinstance(node,ast.Name):return inputs[node.id]
        if isinstance(node,ast.UnaryOp) and isinstance(node.op,ast.USub):return -visit(node.operand)
        if isinstance(node,ast.BinOp) and type(node.op) in OPS:return OPS[type(node.op)](visit(node.left),visit(node.right))
        if isinstance(node,ast.Compare) and len(node.ops)==1:
            left,right=visit(node.left),visit(node.comparators[0])
            return np.where(np.isfinite(left)&np.isfinite(right),CMP[type(node.ops[0])](left,right),np.nan)
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in funcs:
            return funcs[node.func.id](*(visit(a) for a in node.args))
        raise ValueError('Unregistered formula syntax')
    with np.errstate(all='ignore'):
        result=visit(ast.parse(formula,mode='eval'))
    return np.where(np.isfinite(result),result,np.nan)

def required_history(formula):
    def span(n):
        if isinstance(n,ast.Name):return 1 if n.id=='returns' else 0
        if isinstance(n,ast.Constant):return 0
        if isinstance(n,ast.Call):
            d=max([span(x) for x in n.args]+[0])
            if n.func.id in {'delay','delta'}:return d+int(n.args[-1].value)
            if n.func.id in {'std','mean','sum','minimum','maximum','argmax','tsrank','corr','cov'}:return d+int(n.args[-1].value)-1
            return d
        return max([span(x) for x in ast.iter_child_nodes(n)]+[0])
    return span(ast.parse(formula,mode='eval'))
