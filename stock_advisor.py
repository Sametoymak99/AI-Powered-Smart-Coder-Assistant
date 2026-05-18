import tkinter as tk
from tkinter import ttk
import yfinance as yf
import pandas as pd
import ta
import webbrowser
from datetime import datetime

# UI.py'den alınan tema renkleri
C_BG = "#020c0c"      # Çok karanlık turkuaz
C_PRI = "#00d4c0"     # Parlak turkuaz (Ana renk)
C_TEXT = "#7dfff6"    # Açık turkuaz (Metin)
C_PANEL = "#030f0f"   # Panel arka planı
C_GREEN = "#00ff88"   # Yeşil (Alım)
C_RED = "#ff3344"     # Kırmızı (Satım)
C_GOLD = "#ffcc00"    # Altın (Nötr/Bilgi)

BIST_STOCKS = [
    "THYAO.IS", "ASELS.IS", "EREGL.IS", "KCHOL.IS", "SISE.IS",
    "GARAN.IS", "AKBNK.IS", "YKBNK.IS", "TUPRS.IS", "BIMAS.IS",
    "SASA.IS", "HEKTS.IS", "GUBRF.IS", "PGSUS.IS", "TOASO.IS",
    "FROTO.IS", "ARCLK.IS", "VESTL.IS", "PETKM.IS", "TTKOM.IS",
    "TCELL.IS", "HALKB.IS", "VAKBN.IS", "ISCTR.IS"
]

def fetch_data(ticker):
    try:
        data = yf.download(ticker, period="3mo", interval="1d", progress=False)
        return data
    except Exception as e:
        print(f"Hata {ticker}: {e}")
        return None

def fetch_news(ticker):
    try:
        t = yf.Ticker(ticker)
        return t.news[:5]
    except Exception as e:
        print(f"Haber çekilemedi {ticker}: {e}")
        return []

def calculate_indicators(df):
    if df is None or len(df) < 20:
        return None
    
    df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
    macd = ta.trend.MACD(df['Close'])
    df['MACD_Diff'] = macd.macd_diff()
    
    bollinger = ta.volatility.BollingerBands(df['Close'], window=20, window_dev=2)
    df['BB_High'] = bollinger.bollinger_hband()
    df['BB_Low'] = bollinger.bollinger_lband()
    
    return df

def generate_signals(df):
    if df is None:
        return "Veri Yok", "N/A", "N/A", "N/A", "0 Al / 0 Sat", "-"
        
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    signals = []
    buy_count = 0
    sell_count = 0
    
    # RSI
    if latest['RSI'] < 35:
        signals.append("RSI Aşırı Satım")
        buy_count += 1
    elif latest['RSI'] > 65:
        signals.append("RSI Aşırı Alım")
        sell_count += 1
        
    # MACD
    if prev['MACD_Diff'] < 0 and latest['MACD_Diff'] > 0:
        signals.append("MACD Al")
        buy_count += 1
    elif prev['MACD_Diff'] > 0 and latest['MACD_Diff'] < 0:
        signals.append("MACD Sat")
        sell_count += 1
        
    # Bollinger
    if latest['Close'] < latest['BB_Low']:
        signals.append("Bollinger Alt")
        buy_count += 1
    elif latest['Close'] > latest['BB_High']:
        signals.append("Bollinger Üst")
        sell_count += 1
        
    # Durum ve Seviye Belirleme
    if buy_count > sell_count:
        status = "GÜÇLÜ AL" if buy_count >= 2 else "AL"
        vade = "Kısa Vade (1-2 Hafta)"
        target_price = latest['Close'] * 1.05
        
        if buy_count == 3:
            level = "★★★"
        elif buy_count == 2:
            level = "★★"
        else:
            level = "★"
            
    elif sell_count > buy_count:
        status = "GÜÇLÜ SAT" if sell_count >= 2 else "SAT"
        vade = "Kısa Vade (1-2 Hafta)"
        target_price = latest['Close'] * 0.95
        level = "-"
    else:
        status = "NÖTR"
        vade = "N/A"
        target_price = latest['Close']
        level = "-"
        
    signal_text = ", ".join(signals) if signals else "Sinyal Yok"
    score_text = f"{buy_count} Al / {sell_count} Sat"
    
    return status, signal_text, f"{target_price:.2f}", vade, score_text, level

class PremiumStockAdvisorUI:
    def __init__(self, root):
        self.root = root
        self.root.title("F.R.I.D.A.Y. — Premium Hisse Analiz & Ajan Platformu")
        self.root.geometry("1100x650")
        self.root.configure(bg=C_BG)
        
        # Stil Ayarları
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        # Treeview Stili
        self.style.configure("Treeview", 
            background=C_PANEL, 
            foreground=C_TEXT, 
            fieldbackground=C_PANEL,
            font=("Consolas", 11),
            rowheight=30,
            borderwidth=0
        )
        self.style.configure("Treeview.Heading", 
            background=C_BG, 
            foreground=C_PRI, 
            font=("Helvetica", 11, "bold"),
            borderwidth=1
        )
        self.style.map("Treeview", background=[("selected", C_PRI)], foreground=[("selected", C_BG)])
        
        # Ana Frame
        self.main_frame = tk.Frame(root, bg=C_BG, padx=15, pady=15)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Üst Başlık Paneli
        self.header_frame = tk.Frame(self.main_frame, bg=C_PANEL, highlightbackground=C_PRI, highlightthickness=1, padx=15, pady=10)
        self.header_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.title_label = tk.Label(self.header_frame, text="F.R.I.D.A.Y. BIST ANALİZ", font=("Helvetica", 20, "bold"), fg=C_PRI, bg=C_PANEL)
        self.title_label.pack(side=tk.LEFT)
        
        self.agent_label = tk.Label(self.header_frame, text="● MASAÜSTÜ AJANI AKTİF", font=("Helvetica", 10, "bold"), fg=C_GREEN, bg=C_PANEL)
        self.agent_label.pack(side=tk.LEFT, padx=20)
        
        # Masaüstü Ajanı Butonu
        self.web_btn = tk.Button(self.header_frame, text="GRAFİKLERİ AÇ (TradingView)", command=self.open_charts, bg=C_GOLD, fg=C_BG, font=("Helvetica", 9, "bold"), padx=10, relief=tk.FLAT)
        self.web_btn.pack(side=tk.LEFT, padx=10)
        
        self.scan_btn = tk.Button(self.header_frame, text="TARAMAYI BAŞLAT", command=self.run_scan, bg=C_PRI, fg=C_BG, font=("Helvetica", 10, "bold"), padx=15, pady=5, relief=tk.FLAT)
        self.scan_btn.pack(side=tk.RIGHT)
        
        # Orta Kısım
        self.content_frame = tk.Frame(self.main_frame, bg=C_BG)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Sol Panel (Tablo)
        self.left_panel = tk.Frame(self.content_frame, bg=C_PANEL, highlightbackground=C_PRI, highlightthickness=1)
        self.left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        columns = ("hisse", "fiyat", "durum", "seviye", "hedef", "vade")
        self.tree = ttk.Treeview(self.left_panel, columns=columns, show="headings")
        self.tree.heading("hisse", text="Hisse")
        self.tree.heading("fiyat", text="Fiyat")
        self.tree.heading("durum", text="Durum")
        self.tree.heading("seviye", text="Seviye")
        self.tree.heading("hedef", text="Hedef")
        self.tree.heading("vade", text="Vade")
        
        self.tree.column("hisse", width=70, anchor="center")
        self.tree.column("fiyat", width=70, anchor="center")
        self.tree.column("durum", width=90, anchor="center")
        self.tree.column("seviye", width=80, anchor="center")
        self.tree.column("hedef", width=70, anchor="center")
        self.tree.column("vade", width=130, anchor="center")
        
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        
        # Sağ Panel (Detay ve Haberler)
        self.right_panel = tk.Frame(self.content_frame, bg=C_PANEL, highlightbackground=C_PRI, highlightthickness=1, padx=15, pady=15)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        self.detail_title = tk.Label(self.right_panel, text="GENEL PİYASA HABERLERİ", font=("Helvetica", 14, "bold"), fg=C_PRI, bg=C_PANEL, pady=5)
        self.detail_title.pack(fill=tk.X)
        
        # Seperator
        self.sep = tk.Frame(self.right_panel, height=2, bg=C_PRI)
        self.sep.pack(fill=tk.X, pady=(0, 10))
        
        self.detail_text = tk.Text(self.right_panel, bg=C_PANEL, fg=C_TEXT, font=("Consolas", 11), wrap="word", borderwidth=0)
        self.detail_text.pack(fill=tk.BOTH, expand=True)
        
        # Alt Durum Çubuğu
        self.status_bar = tk.Label(root, text="Sistem Hazır. Taramayı başlatın.", relief=tk.SUNKEN, anchor=tk.W, bg=C_PANEL, fg=C_TEXT, font=("Helvetica", 10), padx=10, pady=5)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.results_data = {}
        
        # Başlangıçta BIST 100 Haberlerini Yükle
        self.load_general_news()

    def open_charts(self):
        """Masaüstü Ajanı özelliği: Tarayıcıda grafikleri açar."""
        webbrowser.open("https://www.tradingview.com/symbols/BIST-XU100/")
        self.status_bar.config(text="Masaüstü Ajanı: TradingView grafikleri açıldı.")

    def load_general_news(self):
        """Açılışta BIST 100 genel haberlerini yükler."""
        self.detail_text.insert(tk.END, "BIST 100 Gündem Haberleri Çekiliyor...\n\n")
        self.root.update()
        
        news = fetch_news("XU100.IS")
        self.detail_text.delete("1.0", tk.END)
        self.detail_text.insert(tk.END, "GÜNDEMDEKİ PİYASA HABERLERİ\n", "header")
        self.detail_text.tag_config("header", font=("Helvetica", 12, "bold"), foreground=C_PRI)
        
        if news:
            for n in news:
                title = n.get('title', 'Başlıksız')
                pub_date = n.get('publisher', 'Bilinmeyen Kaynak')
                self.detail_text.insert(tk.END, f"● {title}\n  Kaynak: {pub_date}\n\n")
        else:
            self.detail_text.insert(tk.END, "Genel piyasa haberi bulunamadı.\n")

    def on_select(self, event):
        selected_items = self.tree.selection()
        if not selected_items:
            return
            
        item = selected_items[0]
        hisse_code = self.tree.item(item, "values")[0]
        full_code = hisse_code + ".IS"
        
        self.detail_title.config(text=f"{hisse_code} DETAYLARI & HABERLER")
        
        self.detail_text.delete("1.0", tk.END)
        self.detail_text.insert(tk.END, f"Hisse: {hisse_code}\n", "header")
        
        data = self.results_data.get(full_code)
        if data:
            self.detail_text.insert(tk.END, f"Kapanış Fiyatı: {data['Fiyat']} TL\n")
            self.detail_text.insert(tk.END, f"Sinyal Durumu: {data['Durum']}\n")
            self.detail_text.insert(tk.END, f"Fırsat Seviyesi: {data['Seviye']}\n")
            self.detail_text.insert(tk.END, f"Sinyal Skoru: {data['Skor']}\n")
            self.detail_text.insert(tk.END, f"Hedef Fiyat: {data['Hedef']} TL\n")
            self.detail_text.insert(tk.END, f"Tahmini Vade: {data['Vade']}\n")
            self.detail_text.insert(tk.END, f"Detaylar: {data['Sinyaller']}\n\n")
            
        self.detail_text.insert(tk.END, "Hisseye Özel Haberler:\n", "header")
        self.detail_text.tag_config("header", font=("Helvetica", 12, "bold"), foreground=C_PRI)
        
        self.detail_text.insert(tk.END, "Haberler çekiliyor...\n")
        self.root.update()
        
        news = fetch_news(full_code)
        self.detail_text.delete("1.0", tk.END) # Yeniden yaz
        self.detail_text.insert(tk.END, f"Hisse: {hisse_code}\n", "header")
        if data:
            self.detail_text.insert(tk.END, f"Kapanış Fiyatı: {data['Fiyat']} TL\n")
            self.detail_text.insert(tk.END, f"Sinyal Durumu: {data['Durum']}\n")
            self.detail_text.insert(tk.END, f"Fırsat Seviyesi: {data['Seviye']}\n")
            self.detail_text.insert(tk.END, f"Sinyal Skoru: {data['Skor']}\n")
            self.detail_text.insert(tk.END, f"Hedef Fiyat: {data['Hedef']} TL\n")
            self.detail_text.insert(tk.END, f"Tahmini Vade: {data['Vade']}\n")
            self.detail_text.insert(tk.END, f"Detaylar: {data['Sinyaller']}\n\n")
        self.detail_text.insert(tk.END, "Hisseye Özel Haberler:\n", "header")
        
        if news:
            for n in news:
                title = n.get('title', 'Başlıksız')
                pub_date = n.get('publisher', 'Bilinmeyen Kaynak')
                self.detail_text.insert(tk.END, f"● {title}\n  Kaynak: {pub_date}\n\n")
        else:
            self.detail_text.insert(tk.END, "Bu hisse için yakın zamanda haber bulunamadı.\n")

    def run_scan(self):
        self.status_bar.config(text="Tarama yapılıyor, lütfen bekleyin...")
        self.root.update()
        
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        self.results_data.clear()
        
        for ticker in BIST_STOCKS:
            self.status_bar.config(text=f"Taranıyor: {ticker}")
            self.root.update()
            
            df = fetch_data(ticker)
            df = calculate_indicators(df)
            
            if df is not None:
                status, signals, target, vade, score, level = generate_signals(df)
                close_price = df.iloc[-1]['Close']
                
                hisse_name = ticker.replace(".IS", "")
                self.results_data[ticker] = {
                    "Fiyat": f"{close_price:.2f}",
                    "Durum": status,
                    "Hedef": target,
                    "Vade": vade,
                    "Skor": score,
                    "Seviye": level,
                    "Sinyaller": signals
                }
                
                # Tabloya ekle
                item_id = self.tree.insert("", tk.END, values=(hisse_name, f"{close_price:.2f}", status, level, target, vade))
                
                # Renklendirme
                if "AL" in status:
                    self.tree.tag_configure("green", foreground=C_GREEN)
                    self.tree.item(item_id, tags=("green",))
                elif "SAT" in status:
                    self.tree.tag_configure("red", foreground=C_RED)
                    self.tree.item(item_id, tags=("red",))
                    
        self.status_bar.config(text=f"Tarama tamamlandı. {len(self.results_data)} hisse incelendi.")

def main():
    root = tk.Tk()
    app = PremiumStockAdvisorUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
