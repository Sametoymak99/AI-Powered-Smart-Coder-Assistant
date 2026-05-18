import tkinter as tk
from tkinter import ttk
import yfinance as yf
import pandas as pd
import ta
from datetime import datetime, timedelta

# BIST Hisse Listesi (En aktif hisselerden bir derleme)
# Gerçekte tüm BIST hisseleri eklenebilir ancak Yahoo Finance kısıtlamaları için başlangıçta makul bir liste seçilmiştir.
BIST_STOCKS = [
    "THYAO.IS", "ASELS.IS", "EREGL.IS", "KCHOL.IS", "SISE.IS",
    "GARAN.IS", "AKBNK.IS", "YKBNK.IS", "TUPRS.IS", "BIMAS.IS",
    "SASA.IS", "HEKTS.IS", "GUBRF.IS", "PGSUS.IS", "TOASO.IS",
    "FROTO.IS", "ARCLK.IS", "VESTL.IS", "PETKM.IS", "TTKOM.IS",
    "TCELL.IS", "HALKB.IS", "VAKBN.IS", "ISCTR.IS", "SOKM.IS",
    "MGROS.IS", "ENKAI.IS", "SAHOL.IS", "KOZAL.IS", "KOZAA.IS"
]

def fetch_data(ticker):
    """Hisse verilerini çeker."""
    try:
        # Son 3 aylık veriyi çekiyoruz (İndikatörler için yeterli)
        data = yf.download(ticker, period="3mo", interval="1d", progress=False)
        return data
    except Exception as e:
        print(f"Hata {ticker}: {e}")
        return None

def calculate_indicators(df):
    """Gelişmiş indikatörleri hesaplar."""
    if df is None or len(df) < 20:
        return None
    
    # RSI
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    
    # MACD
    macd = ta.trend.MACD(df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    df['MACD_Diff'] = macd.macd_diff()
    
    # Bollinger Bands
    bollinger = ta.volatility.BollingerBands(df['Close'], window=20, window_dev=2)
    df['BB_High'] = bollinger.bollinger_hband()
    df['BB_Low'] = bollinger.bollinger_lband()
    df['BB_Mid'] = bollinger.bollinger_mavg()
    
    return df

def generate_signals(df):
    """Alım-Satım sinyalleri üretir."""
    if df is None:
        return "Veri Yok", "N/A"
        
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    signals = []
    
    # RSI Sinyali
    if latest['RSI'] < 35:
        signals.append("RSI Aşırı Satım (Alım Fırsatı)")
    elif latest['RSI'] > 65:
        signals.append("RSI Aşırı Alım (Kâr Al/Sat)")
        
    # MACD Sinyali (Kesişim)
    if prev['MACD_Diff'] < 0 and latest['MACD_Diff'] > 0:
        signals.append("MACD Yukarı Kesti (Al)")
    elif prev['MACD_Diff'] > 0 and latest['MACD_Diff'] < 0:
        signals.append("MACD Aşağı Kesti (Sat)")
        
    # Bollinger Sinyali
    if latest['Close'] < latest['BB_Low']:
        signals.append("Bollinger Alt Bandı (Destek/Al)")
    elif latest['Close'] > latest['BB_High']:
        signals.append("Bollinger Üst Bandı (Direnç/Sat)")
        
    # Genel Durum
    if any("Al" in s for s in signals):
        status = "GÜÇLÜ AL" if len([s for s in signals if "Al" in s]) > 1 else "AL"
    elif any("Sat" in s for s in signals):
        status = "GÜÇLÜ SAT" if len([s for s in signals if "Sat" in s]) > 1 else "SAT"
    else:
        status = "NÖTR"
        
    signal_text = ", ".join(signals) if signals else "Belirgin Sinyal Yok"
    
    # Basit Hedef Fiyat (Örn: Son Kapanış + %5)
    target_price = latest['Close'] * 1.05 if "Al" in status else "N/A"
    if isinstance(target_price, float):
        target_price = f"{target_price:.2f}"
        
    return status, signal_text, target_price

def scan_stocks():
    """Tüm listeyi tarar ve sonuçları döner."""
    results = []
    for ticker in BIST_STOCKS:
        print(f"Taranıyor: {ticker}")
        df = fetch_data(ticker)
        df = calculate_indicators(df)
        if df is not None:
            status, signals, target = generate_signals(df)
            close_price = df.iloc[-1]['Close']
            results.append({
                "Hisse": ticker.replace(".IS", ""),
                "Fiyat": f"{close_price:.2f}",
                "Durum": status,
                "Hedef": target,
                "Sinyaller": signals
            })
    return results

class StockAdvisorUI:
    def __init__(self, root):
        self.root = root
        self.root.title("F.R.I.D.A.Y. - BIST Hisse Tarayıcı ve Öneri Sistemi")
        self.root.geometry("800x500")
        
        # Tema ve Stil
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        # Üst Panel
        self.top_frame = ttk.Frame(root, padding=10)
        self.top_frame.pack(fill=tk.X)
        
        self.title_label = ttk.Label(self.top_frame, text="BIST Hisse Tarayıcı", font=("Helvetica", 16, "bold"))
        self.title_label.pack(side=tk.LEFT)
        
        self.scan_btn = ttk.Button(self.top_frame, text="Tarama Başlat", command=self.run_scan)
        self.scan_btn.pack(side=tk.RIGHT)
        
        # Tablo
        self.table_frame = ttk.Frame(root, padding=10)
        self.table_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("hisse", "fiyat", "durum", "hedef", "sinyaller")
        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings")
        
        self.tree.heading("hisse", text="Hisse Kodu")
        self.tree.heading("fiyat", text="Son Fiyat")
        self.tree.heading("durum", text="Durum")
        self.tree.heading("hedef", text="Hedef Fiyat (+%5)")
        self.tree.heading("sinyaller", text="Detay Sinyaller")
        
        self.tree.column("hisse", width=80)
        self.tree.column("fiyat", width=80)
        self.tree.column("durum", width=100)
        self.tree.column("hedef", width=100)
        self.tree.column("sinyaller", width=300)
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # Durum Çubuğu
        self.status_bar = ttk.Label(root, text="Hazır. Tarama başlatmak için butona tıklayın.", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def run_scan(self):
        self.status_bar.config(text="Tarama yapılıyor, lütfen bekleyin...")
        self.root.update()
        
        # Tabloyu temizle
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        results = scan_stocks()
        
        for res in results:
            self.tree.insert("", tk.END, values=(res["Hisse"], res["Fiyat"], res["Durum"], res["Hedef"], res["Sinyaller"]))
            
        self.status_bar.config(text=f"Tarama tamamlandı. {len(results)} hisse incelendi.")

def main():
    root = tk.Tk()
    app = StockAdvisorUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
