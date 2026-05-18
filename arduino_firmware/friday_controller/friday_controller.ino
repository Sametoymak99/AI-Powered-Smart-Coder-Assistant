/*
 * F.R.I.D.A.Y Arduino Controller Firmware (DHT11 + RFID Versiyonu)
 */

#include <SPI.h>
#include <MFRC522.h>
#include "DHT.h"

#define SS_PIN 10
#define RST_PIN 9
#define DHTPIN 2
#define DHTTYPE DHT11

MFRC522 rfid(SS_PIN, RST_PIN);
DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(9600);
  SPI.begin();
  rfid.PCD_Init();
  dht.begin();
  
  // F.R.I.D.A.Y bağlandığında hazır olduğunu bildirir
  Serial.println("FRIDAY_READY");
}

void loop() {
  // 1. RFID Kontrolü (Asenkron bildirim)
  if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
    String uidString = "";
    for (byte i = 0; i < rfid.uid.size; i++) {
      uidString += String(rfid.uid.uidByte[i] < 0x10 ? "0" : "");
      uidString += String(rfid.uid.uidByte[i], HEX);
    }
    uidString.toUpperCase();
    
    // F.R.I.D.A.Y'e kartın okunduğunu haber ver
    Serial.println("EVENT_RFID:" + uidString);
    
    // Aynı kartın sürekli okunmasını önlemek için
    rfid.PICC_HaltA();
    delay(500); // Küçük bir bekleme
  }

  // 2. F.R.I.D.A.Y'den gelen komutları dinleme
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim(); 
    
    if (command == "GET_TEMP") {
      float t = dht.readTemperature();
      float h = dht.readHumidity();

      if (isnan(t) || isnan(h)) {
        Serial.println("ERROR: Sensörden veri okunamadı! Kabloları kontrol et.");
      } else {
        Serial.print("DATA: Sicaklik ");
        Serial.print(t);
        Serial.print(" derece, Nem yuzde ");
        Serial.println(h);
      }
    }
    else if (command == "PING") {
      Serial.println("PONG");
    }
    else {
      Serial.println("ERROR: Bilinmeyen komut (" + command + ")");
    }
  }
}
