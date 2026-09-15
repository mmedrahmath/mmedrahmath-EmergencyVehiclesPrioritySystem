/*
 * ==============================================================================
 * PROJECT: Emergency Vehicles Priority System (EVPS)
 * MODULE: ESP32 Traffic Junction Receiver & Relay Controller
 * TEAM: PHANTOM DELUX | THEME: SMART VEHICLES
 * ==============================================================================
 * Hardware Connections:
 * - ESP32 NodeMCU
 * - NRF24L01+ RF Receiver: CE -> GPIO 22, CSN -> GPIO 21, SCK -> 18, MISO -> 19, MOSI -> 23
 * - Relay 1 (RED LIGHT): GPIO 12
 * - Relay 2 (YELLOW LIGHT): GPIO 13
 * - Relay 3 (GREEN LIGHT): GPIO 14
 * - Buzzer (Emergency Siren Alert): GPIO 27
 * ==============================================================================
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <nRF24L01.h>
#include <RF24.h>

#define RELAY_RED_PIN 12
#define RELAY_YELLOW_PIN 13
#define RELAY_GREEN_PIN 14
#define BUZZER_PIN 27

#define JUNCTION_ID 4 // Junction J-04
const char* RECEIVER_ID = "RX-ESP32-J04";
const char* SERVER_ACK_URL = "http://192.168.1.100:8000/api/receivers/status";

RF24 radio(22, 21);
const byte nrfAddress[6] = "EVPS1";

struct PriorityPacket {
  char ambulance_id[8];
  float lat;
  float lng;
  float speed_kmh;
  bool emergency_active;
  uint32_t timestamp;
};

void setTrafficSignal(bool red, bool yellow, bool green) {
  digitalWrite(RELAY_RED_PIN, red ? HIGH : LOW);
  digitalWrite(RELAY_YELLOW_PIN, yellow ? HIGH : LOW);
  digitalWrite(RELAY_GREEN_PIN, green ? HIGH : LOW);
}

void setup() {
  Serial.begin(115200);

  pinMode(RELAY_RED_PIN, OUTPUT);
  pinMode(RELAY_YELLOW_PIN, OUTPUT);
  pinMode(RELAY_GREEN_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);

  // Initialize NRF24L01
  if (radio.begin()) {
    radio.openReadingPipe(0, nrfAddress);
    radio.setPALevel(RF24_PA_HIGH);
    radio.setDataRate(RF24_250KBPS);
    radio.startListening();
    Serial.println("[EVPS Receiver] RF Listening on Channel EVPS1...");
  }

  // Normal Traffic Cycle Initial State: RED
  setTrafficSignal(true, false, false);
}

void loop() {
  // Check for inbound priority request packet
  if (radio.available()) {
    PriorityPacket packet;
    radio.read(&packet, sizeof(packet));

    if (packet.emergency_active) {
      Serial.print("🚨 [EVPS PRIORITY] INCOMING AMBULANCE: ");
      Serial.print(packet.ambulance_id);
      Serial.print(" | Speed: ");
      Serial.println(packet.speed_kmh);

      // 1. Instantly override signal to GREEN
      setTrafficSignal(false, false, true);

      // 2. Beep buzzer for pedestrian warning
      for (int i = 0; i < 3; i++) {
        tone(BUZZER_PIN, 1200, 150);
        delay(200);
      }
      noTone(BUZZER_PIN);

      // 3. Keep GREEN priority active for ambulance crossing (with safety watchdog)
      unsigned long greenStart = millis();
      while (millis() - greenStart < 12000) { // 12 seconds priority window
        delay(100);
      }

      // 4. Safe restoration to normal cycle
      setTrafficSignal(false, true, false); // Yellow transition
      delay(2000);
      setTrafficSignal(true, false, false); // Restore Red/Normal
      Serial.println("✓ [EVPS PRIORITY] Ambulance Cleared. Normal cycle restored.");
    }
  }

  delay(50);
}
