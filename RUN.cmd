@echo off
setlocal EnableDelayedExpansion
title MomoRider / Trading Toolkit
cd /d "%~dp0"

REM ---------------------------------------------------------------- find python
set "PY="
for %%P in (
  "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
  "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
) do if not defined PY if exist %%P set "PY=%%~P"
if not defined PY (
  py -3 -c "import sys" >nul 2>&1 && set "PY=py -3"
)
if not defined PY (
  where python >nul 2>&1 && set "PY=python"
)
if not defined PY (
  echo.
  echo   Python was not found. Install Python 3.11+ from python.org, tick
  echo   "Add python.exe to PATH" during setup, then run this again.
  echo.
  pause
  exit /b 1
)

:menu
cls
echo.
echo   ===========================================================
echo      MomoRider / Trading Toolkit
echo   ===========================================================
echo.
echo      DAILY
echo        1.  Momentum basket scan   ^(the main tool - run every 5 days^)
echo        2.  Refresh GEX regime for MT5   ^(run before the US close^)
echo        3.  Do both
echo.
echo      SETUP / CHECKS
echo        4.  Check + install Python packages
echo        5.  Show today's saved basket
echo        6.  Where do my indicator files go?
echo.
echo      VERIFY THE RESEARCH  ^(slow - several minutes each^)
echo        7.  Re-run cross-sectional validation ^(the Sharpe 2.18 result^)
echo        8.  Re-run stress tests ^(costs / funding / survivorship^)
echo        9.  Re-run permutation test
echo.
echo        0.  Exit
echo.
set "choice="
set /p "choice=   Choose: "

if "%choice%"=="1" goto scan
if "%choice%"=="2" goto gex
if "%choice%"=="3" goto both
if "%choice%"=="4" goto deps
if "%choice%"=="5" goto basket
if "%choice%"=="6" goto where
if "%choice%"=="7" goto valid
if "%choice%"=="8" goto stress
if "%choice%"=="9" goto perm
if "%choice%"=="0" exit /b 0
goto menu

:scan
cls
echo   Pulling live daily data from Bybit...
echo.
%PY% "momentum_system\backtest\scanner.py"
if errorlevel 1 echo.  ^>^> Scan failed. Check your internet connection.
goto done

:gex
cls
echo   Computing dealer gamma from a free option chain...
echo.
%PY% "orderflow\backtest\run_gex.py" SPY
if errorlevel 1 echo.  ^>^> GEX fetch failed - Yahoo may be rate-limiting. Try again in a minute.
goto done

:both
cls
echo   [1/2] Momentum basket
echo.
%PY% "momentum_system\backtest\scanner.py"
echo.
echo   -----------------------------------------------------------
echo   [2/2] GEX regime
echo.
%PY% "orderflow\backtest\run_gex.py" SPY
goto done

:deps
cls
echo   Checking packages...
echo.
%PY% -c "import importlib,sys; miss=[m for m in ['requests','numpy','scipy','pandas','yfinance','MetaTrader5','sklearn'] if not importlib.util.find_spec(m)]; print('   missing:', miss if miss else 'nothing - all good'); sys.exit(1 if miss else 0)"
if errorlevel 1 (
   echo.
   echo   Installing the missing ones...
   %PY% -m pip install --quiet --upgrade requests numpy scipy pandas yfinance MetaTrader5 scikit-learn
   echo   Done.
)
goto done

:basket
cls
if exist "momentum_system\data\basket.json" (
   echo   Last saved basket:
   echo.
   type "momentum_system\data\basket.json"
) else (
   echo   No basket saved yet - run option 1 first.
)
goto done

:where
cls
echo.
echo   TRADINGVIEW  ^(paste the file contents into Pine Editor, then "Add to chart"^)
echo     momentum_system\XSectionalMomentum.pine    ranking table + LONG/SHORT tint
echo     indicators\4_JS_Ribbon_Liquidity_Combined.pine
echo     indicators\5_JS_MomoRider_Momentum_v2.pine
echo     strategy\MomoRider_Strategy.pine
echo.
echo   METATRADER 5  ^(already installed + compiled in both your terminals^)
echo     MQL5\Indicators\MomoRider\MomoRider_Ribbon.mq5
echo     MQL5\Indicators\MomoRider\MomoRider_Momentum.mq5
echo     MQL5\Indicators\MomoRider\MIM_GEX.mq5
echo     In MT5: Navigator ^> Indicators ^> MomoRider
echo.
echo   READ FIRST
echo     momentum_system\README.md    the strategy that tested well ^(Sharpe 2.18^)
echo     strategy\README.md           why 4G/4R did not work
echo     orderflow\README.md          the gamma trade + where to get L1/L2/L3 data
echo.
goto done

:valid
cls
echo   Re-running the cross-sectional grid. Takes a few minutes...
echo.
pushd momentum_system\backtest
%PY% xsec.py
popd
goto done

:stress
cls
echo   Re-running stress tests. Takes a few minutes...
echo.
pushd momentum_system\backtest
%PY% xsec_stress.py
popd
goto done

:perm
cls
echo   Re-running the permutation test. This one is slow ^(60 shuffles^)...
echo.
pushd momentum_system\backtest
%PY% perm_test.py
popd
goto done

:done
echo.
echo   -----------------------------------------------------------
pause
goto menu
