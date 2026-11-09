"""Run once a day (before the close) to refresh the gamma regime for MT5."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gex import export_regime
if __name__ == "__main__":
    tk = sys.argv[1:] or ["SPY"]
    print(f"fetching dealer gamma for {tk} ...")
    export_regime(tuple(tk), extra_dirs=(os.path.join(os.path.dirname(__file__), "..", "data"),))
