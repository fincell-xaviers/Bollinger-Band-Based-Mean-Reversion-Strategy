import yfinance as yf
from datetime import datetime
import pandas as pd
import numpy as np
import plotly.express as px
ticker = "RELIANCE.NS"
start_date = "2020-01-01"
end_date = datetime.now().strftime('%Y-%m-%d')

df = yf.download(ticker, start=start_date, end=end_date)
display(df.head())
df.columns = df.columns.get_level_values(0)


df = df.rename(columns={
    'Open': 'open',
    'High': 'high',
    'Low': 'low',
    'Close': 'close',
    'Volume': 'tick_volume'
})


df['sma'] = df['close'].rolling(20).mean()

df['sd'] = df['close'].rolling(20).std()

df['lb'] = df['sma'] - 2 * df['sd']

df['ub'] = df['sma'] + 2 * df['sd']

df.dropna(inplace=True)
display(df.head())
def find_signal(close, lower_band, upper_band):
    if close < lower_band:
        return 'buy'
    elif close > upper_band:
        return 'sell'
    else:
        return None


df['signal'] = np.vectorize(find_signal)(df['close'], df['lb'], df['ub'])

display(df.head())
import plotly.graph_objects as go
import plotly.express as go_px

df_plot = df.reset_index()
df_plot = df_plot.rename(columns={'Date': 'time'})


fig = go_px.line(df_plot, x='time', y=['close', 'sma', 'lb', 'ub'])


buy_signals = df_plot[df_plot['signal'] == 'buy']
fig.add_trace(go.Scatter(x=buy_signals['time'], y=buy_signals['close'],
                         mode='markers', name='Buy Signal',
                         marker=dict(color='green', size=8, symbol='triangle-up')))

sell_signals = df_plot[df_plot['signal'] == 'sell']
fig.add_trace(go.Scatter(x=sell_signals['time'], y=sell_signals['close'],
                         mode='markers', name='Sell Signal',
                         marker=dict(color='red', size=8, symbol='triangle-down')))


fig.update_layout(title='Close Price with Bollinger Bands and Trading Signals',
                  xaxis_title='Time',
                  yaxis_title='Price')


fig.show()
import numpy as np
import pandas as pd

initial_capital = 100_000.0
fee_bps, slip_bps = 5.0, 5.0

def pay(px, side):
    m = 1 + (fee_bps+slip_bps)/10_000 if side==+1 else 1 - (fee_bps+slip_bps)/10_000
    return px*m

bt = df.copy().sort_index()
bt['Signal'] = bt['signal'].map({'buy':1, 'sell':-1}).fillna(0).astype(int)
bt['ExecSignal'] = bt['Signal'].shift(1).fillna(0).astype(int)

price_col = 'close'
exec_price_col = 'open' if 'open' in bt.columns else 'close'

cash, shares = initial_capital, 0.0
equity, cash_s, shares_s, pos_s = [], [], [], []
trades = []

for ts, row in bt.iterrows():
    px = float(row[price_col])
    ex = float(row.get(exec_price_col, px))
    sig = int(row['ExecSignal'])

    if sig == 1 and shares == 0:
        fill = pay(ex, +1)
        shares = cash / fill
        trades.append({'date': ts, 'side':'BUY', 'price': fill, 'shares': shares})
        cash = 0.0
    elif sig == -1 and shares > 0:
        fill = pay(ex, -1)
        cash = shares * fill
        trades.append({'date': ts, 'side':'SELL', 'price': fill, 'shares': 0.0})
        shares = 0.0

    equity.append(cash + shares*px)
    cash_s.append(cash)
    shares_s.append(shares)
    pos_s.append(1 if shares>0 else 0)

bt['Equity'] = equity
bt['Cash'] = cash_s
bt['Shares'] = shares_s
bt['Position'] = pos_s

bh_price0 = float(bt.iloc[0][exec_price_col] if exec_price_col in bt.columns else bt.iloc[0][price_col])
bh_shares = initial_capital / bh_price0
bt['BH_Equity'] = bh_shares * bt[price_col]

bt['StratRet'] = bt['Equity'].pct_change().fillna(0.0)
bt['BH_Ret'] = bt['BH_Equity'].pct_change().fillna(0.0)

def sharpe(r, n=252):
    mu, sd = r.mean()*n, r.std(ddof=0)*np.sqrt(n)
    return np.nan if sd==0 else mu/sd

def mdd(eq):
    peak = eq.cummax()
    return (eq/peak - 1).min()

summary = pd.DataFrame({
    'Final Equity':[bt['Equity'].iloc[-1]],
    'Total Return %':[ (bt['Equity'].iloc[-1]/initial_capital - 1)*100 ],
    'Sharpe':[ sharpe(bt['StratRet']) ],
    'Max Drawdown %':[ mdd(bt['Equity'])*100 ],
    'BH Final Equity':[bt['BH_Equity'].iloc[-1]],
    'BH Total Return %':[ (bt['BH_Equity'].iloc[-1]/initial_capital - 1)*100 ],
    'BH Sharpe':[ sharpe(bt['BH_Ret']) ],
    'BH Max Drawdown %':[ mdd(bt['BH_Equity'])*100 ],
    'Trades':[ int(bt['Position'].diff().abs().sum()) ]
})
print(summary.round(3))
import pandas as pd
import matplotlib.pyplot as plt

summary_df = pd.DataFrame(summary)

styled = (
    summary_df
    .round({
        'Final Equity': 0, 'BH Final Equity': 0,
        'Total Return %': 2, 'BH Total Return %': 2,
        'Sharpe': 3, 'BH Sharpe': 3,
        'Max Drawdown %': 2, 'BH Max Drawdown %': 2
    })
    .style
    .format({
        'Final Equity': '₹{:,.0f}',
        'BH Final Equity': '₹{:,.0f}',
        'Total Return %': '{:.2f}%',
        'BH Total Return %': '{:.2f}%',
        'Sharpe': '{:.3f}',
        'BH Sharpe': '{:.3f}',
        'Max Drawdown %': '{:.2f}%',
        'BH Max Drawdown %': '{:.2f}%',
        'Trades': '{:d}'
    })
    .set_caption("Backtesting Performance Summary")
    .hide(axis="index")
)
display(styled)


plt.figure(figsize=(12,6))
plt.plot(bt.index, bt['Equity'], label='Strategy', color='royalblue')
plt.plot(bt.index, bt['BH_Equity'], label='Buy & Hold', color='gray', linestyle='--')
plt.title('Equity Curve: Strategy vs. Buy & Hold', fontsize=14)
plt.xlabel('Date'); plt.ylabel('Portfolio Value (₹)')
plt.legend(); plt.grid(True, linestyle=':')
plt.show()


if 'ub' in bt.columns and 'lb' in bt.columns and 'sma' in bt.columns and 'close' in bt.columns:
    buys  = bt[bt['ExecSignal'] == 1]
    sells = bt[bt['ExecSignal'] == -1]

    plt.figure(figsize=(12,6))
    plt.plot(bt.index, bt['close'], label='Close', color='black', alpha=0.6)
    plt.plot(bt.index, bt['ub'], label='Upper Band', color='red', linestyle='--')
    plt.plot(bt.index, bt['sma'], label='Middle Band', color='blue', linestyle=':')
    plt.plot(bt.index, bt['lb'], label='Lower Band', color='green', linestyle='--')
    plt.scatter(buys.index,  buys['close'],  marker='^', color='lime',  label='Buy', s=80)
    plt.scatter(sells.index, sells['close'], marker='v', color='crimson', label='Sell', s=80)
    plt.title('Bollinger Bands with Buy/Sell Points', fontsize=14)
    plt.xlabel('Date'); plt.ylabel('Price')
    plt.legend(); plt.grid(True, linestyle=':')
    plt.show()



import numpy as np, pandas as pd

stop_loss_pct   = 0.05
initial_capital = 100_000.0
fee_bps, slip_bps = 5.0, 5.0

def pay(px, side):
    m = 1 + (fee_bps+slip_bps)/10_000 if side==+1 else 1 - (fee_bps+slip_bps)/10_000
    return px*m

def sharpe(r, n=252):
    r = pd.Series(r).dropna()
    return np.nan if r.std(ddof=0)==0 else (r.mean()*n)/(r.std(ddof=0)*np.sqrt(n))

def mdd(eq):
    eq = pd.Series(eq)
    return (eq/eq.cummax() - 1).min()

def build_bbands(df, n, k):
    d = df.copy()
    d['SMA'] = d['close'].rolling(n).mean()
    d['STD'] = d['close'].rolling(n).std()
    d['UB']  = d['SMA'] + k*d['STD']
    d['LB']  = d['SMA'] - k*d['STD']
    return d.dropna()

def build_signals(df):
    d = df.copy(); d['Signal']=0
    d.loc[(d['close'].shift(1)>=d['LB'].shift(1))&(d['close']<d['LB']),'Signal']=1
    d.loc[(d['close'].shift(1)<=d['SMA'].shift(1))&(d['close']>d['SMA']),'Signal']=-1
    return d

def pair_trades(trades):
    if not trades: return pd.DataFrame()
    log=pd.DataFrame(trades).sort_values('date')
    entries, exits=[],[]
    hold=False
    for _,r in log.iterrows():
        if r['side'].startswith('BUY') and not hold:
            hold=True; ep=r['price']; et=r['date']
        elif r['side'].startswith('SELL') and hold:
            entries.append({'entry_time':et,'entry_price':ep})
            exits.append({'exit_time':r['date'],'exit_price':r['price']})
            hold=False
    if not entries or not exits: return pd.DataFrame()
    t=pd.concat([pd.DataFrame(entries),pd.DataFrame(exits)],axis=1)
    t['ret_pct']=(t['exit_price']/t['entry_price']-1)*100
    return t

n_values=[20,50,100]; k_values=[1.5,2.0,2.5]
all_results=[]

for n in n_values:
    for k in k_values:
        df_tmp=build_bbands(df,n,k)
        if df_tmp.empty: continue
        bt=build_signals(df_tmp); bt['ExecSignal']=bt['Signal'].shift(1).fillna(0)
        cash,shares=initial_capital,0.0
        equity=[]; trades=[]; peak=np.nan
        for ts,row in bt.iterrows():
            px=float(row['close']); ex=float(row.get('open',px)); sig=int(row['ExecSignal'])
            stop=False
            if shares>0:
                peak=px if np.isnan(peak) else max(peak,px)
                if px<=peak*(1-stop_loss_pct): stop=True
            if sig==1 and shares==0:
                fill=pay(ex,+1); shares=cash/fill; cash=0.0
                trades.append({'date':ts,'side':'BUY','price':fill})
                peak=px
            elif (sig==-1 and shares>0) or stop:
                fill=pay(ex,-1); cash=shares*fill; shares=0.0
                trades.append({'date':ts,'side':'SELL','price':fill})
                peak=np.nan
            equity.append(cash+shares*px)
        bt['Equity']=equity
        bt['StratRet']=bt['Equity'].pct_change().fillna(0)
        bh_shares=initial_capital/float(bt.iloc[0]['close'])
        bt['BH_Equity']=bh_shares*bt['close']; bt['BH_Ret']=bt['BH_Equity'].pct_change().fillna(0)
        tdf=pair_trades(trades)
        if not tdf.empty:
            wins=tdf[tdf.ret_pct>0].ret_pct; losses=tdf[tdf.ret_pct<=0].ret_pct
            wl=len(wins)/len(losses) if len(losses)>0 else np.inf
            avg_win=wins.mean() if len(wins) else np.nan
        else:
            wl,avg_win=np.nan,np.nan
        all_results.append({
            'n':n,'k':k,'Final Eq':bt['Equity'].iloc[-1],
            'TotRet %':(bt['Equity'].iloc[-1]/initial_capital-1)*100,
            'Sharpe':sharpe(bt['StratRet']),
            'MaxDD %':mdd(bt['Equity'])*100,
            'Trades':len(tdf),'Win/Loss':wl,'Avg Win %':avg_win
        })

results=pd.DataFrame(all_results)
display(results.sort_values(['Sharpe','TotRet %'],ascending=[False,False]).round(3))
import seaborn as sns
import matplotlib.pyplot as plt

pivot_return = results.pivot(index='n', columns='k', values='TotRet %')
pivot_sharpe = results.pivot(index='n', columns='k', values='Sharpe')

fig, ax = plt.subplots(1, 2, figsize=(12,5))

sns.heatmap(pivot_return, annot=True, fmt=".1f", cmap="viridis", ax=ax[0])
ax[0].set_title("Total Return (%) by n and k")
ax[0].set_xlabel("k (band width)")
ax[0].set_ylabel("n (lookback period)")

sns.heatmap(pivot_sharpe, annot=True, fmt=".2f", cmap="magma", ax=ax[1])
ax[1].set_title("Sharpe Ratio by n and k")
ax[1].set_xlabel("k (band width)")
ax[1].set_ylabel("n (lookback period)")

plt.tight_layout()
plt.show()


results_sorted = results.sort_values("Sharpe", ascending=False)

fig, ax1 = plt.subplots(figsize=(10,5))


ax1.bar(results_sorted.index, results_sorted["TotRet %"], color="skyblue", label="Total Return %")
ax1.set_ylabel("Total Return (%)", color="skyblue")
ax1.tick_params(axis='y', labelcolor="skyblue")


ax2 = ax1.twinx()
ax2.plot(results_sorted.index, results_sorted["Sharpe"], color="orange", marker="o", label="Sharpe Ratio")
ax2.set_ylabel("Sharpe Ratio", color="orange")
ax2.tick_params(axis='y', labelcolor="orange")

fig.suptitle("Strategy Performance by Parameter Set", fontsize=14)
fig.tight_layout()
plt.show()

plt.figure(figsize=(8,6))
plt.scatter(results["MaxDD %"], results["TotRet %"],
            c=results["Sharpe"], cmap="coolwarm", s=150, edgecolors='k')
for i, row in results.iterrows():
    plt.text(row["MaxDD %"]+0.2, row["TotRet %"], f"n={row.n},k={row.k}", fontsize=8)

plt.xlabel("Max Drawdown (%)")
plt.ylabel("Total Return (%)")
plt.title("Risk–Reward Tradeoff across Parameters")
plt.colorbar(label="Sharpe Ratio")
plt.show()
