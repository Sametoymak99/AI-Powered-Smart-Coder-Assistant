@echo off
:: F.R.I.D.A.Y. — Görünmez Alkış Başlatıcı Çalıştırma Dosyası
:: Bu dosyayı çift tıklayarak veya Windows Başlangıç klasörüne (startup) ekleyerek 
:: asistanı tamamen arka planda sessizce dinleme moduna alabilirsiniz.

cd /d "%~dp0"
start "" /B pyw -3 "%~dp0clap_launcher.py"
exit
