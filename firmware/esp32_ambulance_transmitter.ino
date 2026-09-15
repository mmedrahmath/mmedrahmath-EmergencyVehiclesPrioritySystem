/*
 * ==============================================================================
 * PROJECT: Emergency Vehicles Priority System (EVPS)
 * MODULE: ESP32 Ambulance Transmitter
 * TEAM: PHANTOM DELUX | THEME: SMART VEHICLES
 * ==============================================================================
 * Hardware Connections:
 * - ESP32 NodeMCU
 * - u-blox NEO-6M GPS: RX -> GPIO 17, TX -> GPIO 16, VCC -> 3.3V, GND -> GND
 * - NRF24L01+ RF Module: CE -> GPIO 22, CSN -> GPIO 21, SCK -> 18, MISO -> 19, MOSI -> 23
 * - Emergency Push Button: GPIO 4 (Pull-Up)
 * - Status LED: GPIO 2
 * ==============================================================================
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <TinyGPSPlus.h>
#include <SPI.h>
#include <nRF24L01.h>
#include <RF24.h>

#define GPS_RX_PIN 16
#define GPS_TX_PIN 17
#define EMERGENCY_BTN_PIN 4
#define STATUS_LED_PIN 2
#define NRF_CE_PIN 22
#define NRF_CSN_PIN 21

// HARDWARE IDENTIFIERS
const char* DEVICE_ID = "TX-ESP32-A001";
const char* AMBULANCE_ID = "A-001";
const char* SERVER_URL = "http://192.168.1.100:8000/api/ambulances/location";

// WiFi Credentials (Optional for direct telemetry push)
const char* WIFI_SSID = "EVPS_DISPATCH_NET";
const char* WIFI_PASS = "Emergency1234";

TinyGPSPlus gps;
HardwareSerial gpsSerial(2);
RF24 radio(NRF_CE_PIN, NRF_CSN_PIN);
const byte nrfAddress[6] = "EVPS1";

struct PriorityPacket {
  char ambulance_id[8];
  float lat;
  float lng;
  float speed_kmh;
  bool emergency_active;
  uint32_t timestamp;
};

bool emergency_active = true;
unsigned long lastTelemetryMillis = 0;

void setup() {
  Serial.begin(115200);
  gpsSerial.begin(9600, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);

  pinMode(EMERGENCY_BTN_PIN, INPUT_PULLUP);
  pinMode(STATUS_LED_PIN, OUTPUT);
  digitalWrite(STATUS_LED_PIN, HIGH);

  // Initialize NRF24L01 RF Module
  if (radio.begin()) {
    radio.openWritingPipe(nrfAddress);
    radio.setPALevel(RF24_PA_HIGH);
    radio.setDataRate(RF24_250KBPS); // Maximum range
    radio.stopListening();
    Serial.println("[EVPS Transmitter] NRF24L01 Initialized Successfully.");
  } else {
    Serial.println("[EVPS Transmitter Error] NRF24L01 Not Responding!");
  }

  // Connect to Wi-Fi if available
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.println("[EVPS] Ambulance Transmitter Online & Ready.");
}

void loop() {
  // 1. Read GPS NMEA Stream
  while (gpsSerial.available() > 0) {
    gps.encode(gpsSerial.read());
  }

  // 2. Read Emergency Toggle Button
  if (digitalRead(EMERGENCY_BTN_PIN) == LOW) {
    emergency_active = !emergency_active;
    digitalWrite(STATUS_LED_PIN, emergency_active ? HIGH : LOW);
    Serial.print("[EVPS] Emergency State Toggled: ");
    Serial.println(emergency_active ? "ACTIVE" : "IDLE");
    delay(300);
  }

  // 3. Periodic Telemetry Broadcast (Every 500ms)
  if (millis() - lastTelemetryMillis >= 500) {
    lastTelemetryMillis = millis();

    float currentLat = gps.location.isValid() ? gps.location.lat() : 28.6145;
    float currentLng = gps.location.isValid() ? gps.location.lng() : 77.2180;
    float currentSpeed = gps.speed.isValid() ? gps.speed.kmph() : 45.0;

    PriorityPacket packet;
    strncpy(packet.ambulance_id, AMBULANCE_ID, sizeof(packet.ambulance_id));
    packet.lat = currentLat;
    packet.lng = currentLng;
    packet.speed_kmh = currentSpeed;
    packet.emergency_active = emergency_active;
    packet.timestamp = millis();

    // Broadcast RF packet to local junction receivers
    radio.write(&packet, sizeof(packet));

    // Send HTTP JSON payload to central EVPS server
    if (WiFi.status() == WL_CONNECTED) {
      HTTPClient http;
      http.begin(SERVER_URL);
      http.addHeader("Content-Type", "application/json");

      String payload = "{\"device_id\":\"" + String(DEVICE_ID) +
                       "\",\"ambulance_id\":\"" + String(AMBULANCE_ID) +
                       "\",\"latitude\":" + String(currentLat, 6) +
                       ",\"longitude\":" + String(currentLng, 6) +
                       ",\"speed\":" + String(currentSpeed, 1) +
                       ",\"emergency_status\":\"" + (emergency_active ? "EMERGENCY_ACTIVE" : "IDLE") +
                       "\",\"gps_status\":\"" + (gps.location.isValid() ? "CONNECTED" : "SEARCHING") + "\"}";

      int httpResponseCode = http.POST(payload);
      http.end();
    }
  }
}
