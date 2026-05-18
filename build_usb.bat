@echo off
echo ==========================================
echo F.R.I.D.A.Y. USB Portatif Surum Olusturucu
echo ==========================================
echo.
echo Gerekli paketler yukleniyor (PyInstaller)...
py -m pip install pyinstaller

echo.
echo Derleme islemi basliyor... Bu islem bilgisayarinizin hizina gore 2-5 dakika surebilir.
echo.

rem PyInstaller ile main.py derleniyor.
rem --noconsole : Arka planda siyah CMD ekranini gizler (Sadece arayuz gorunur)
rem --add-data  : Resim, ses ve font dosyalarinin derlenmis EXE icine gomulmesini saglar.

py -m PyInstaller --noconfirm --onedir --windowed ^
    --add-data "Fonts;Fonts/" ^
    --add-data "Icon;Icon/" ^
    --add-data "SFX;SFX/" ^
    --add-data "memory;memory/" ^
    --add-data "core;core/" ^
    --name "FRIDAY" ^
    main.py

echo.
echo ==========================================
echo ISLEM TAMAMLANDI!
echo ==========================================
echo "dist\FRIDAY" klasoru olusturuldu. 
echo Bu "FRIDAY" klasorunu kopyalayip USB belleginize atabilirsiniz.
echo USB bellegi taktiginiz herhangi bir Windows bilgisayarda Python yuklu olmasa bile FRIDAY.exe dosyasina tiklayarak calistirabilirsiniz!
pause
