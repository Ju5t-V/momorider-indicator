import numpy as np, os, sys, glob, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import load
from engine import Cfg, run, stats

syms = sorted({os.path.basename(f).split("_")[0] for f in glob.glob(os.path.join("..","data","*_30.json"))})
print(f"symbols available on 30m: {syms}\n")
print(f"{'symbol':10} {'n':>5} {'win%':>6} {'meanR':>7} {'totR':>8} {'PF':>6} {'maxDD':>7} {'shrp/t':>7}")
print("-"*66)
allT=[]
cfg = Cfg(sl_atr=1.5, tp_atr=3.0, max_bars=48)   # plain ATR triple barrier, no filters
for s in syms:
    d = load(s,"30")
    tr = run(d, cfg)
    allT += tr
    st = stats(tr)
    if st["n"]==0: print(f"{s:10} {0:5d}"); continue
    print(f"{s:10} {st['n']:5d} {100*st['winrate']:6.1f} {st['meanR']:7.3f} {st['totR']:8.1f} {st['pf']:6.2f} {100*st['maxdd']:6.1f}% {st['sharpe_trade']:7.3f}")
st = stats(allT, bars_per_year=None)
print("-"*66)
print(f"{'POOLED':10} {st['n']:5d} {100*st['winrate']:6.1f} {st['meanR']:7.3f} {st['totR']:8.1f} {st['pf']:6.2f} {100*st['maxdd']:6.1f}% {st['sharpe_trade']:7.3f}")
import collections
print("\nexit reason mix:", dict(collections.Counter(t['why'] for t in allT)))
print("side mix:", dict(collections.Counter(t['side'] for t in allT)))
print(f"median bars held: {np.median([t['bars'] for t in allT]):.0f}")
