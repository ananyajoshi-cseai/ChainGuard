#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <DHT.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>

// =====================================================
// NETWORK
// =====================================================

const char* ssid = "CirkitWifi";
const char* password = "";

// IMPORTANT:
// Replace this with your PUBLIC Render URL.
const char* serverUrl =
    "https://YOUR-URL.onrender.com/api/telemetry";

const char* shipmentId = "CG-1042";


// =====================================================
// PINS
// =====================================================

#define DHTPIN 4
#define DHTTYPE DHT11
#define TAMPER_PIN 5


// =====================================================
// SENSORS
// =====================================================

DHT dht(DHTPIN, DHTTYPE);
Adafruit_MPU6050 mpu;


// =====================================================
// SETUP
// =====================================================

void setup() {

  Serial.begin(115200);

  pinMode(TAMPER_PIN, INPUT_PULLUP);

  // DHT
  dht.begin();

  // MPU6050
  Wire.begin(8, 9);

  if (!mpu.begin()) {
    Serial.println("Failed to discover MPU6050!");
  } else {
    Serial.println("MPU6050 connected.");
  }

  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);


  // =================================================
  // WIFI
  // =================================================

  Serial.print("Connecting to CirkitWifi");

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {

    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("Wi-Fi connected!");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());
}


// =====================================================
// LOOP
// =====================================================

void loop() {

  if (WiFi.status() != WL_CONNECTED) {

    Serial.println("Wi-Fi disconnected.");
    delay(3000);
    return;
  }


  // =================================================
  // READ DHT11
  // =================================================

  float humidity = dht.readHumidity();
  float temperature = dht.readTemperature();

  if (isnan(humidity) || isnan(temperature)) {

    Serial.println("DHT sensor read failed.");
    delay(3000);
    return;
  }


  // =================================================
  // READ MPU6050
  // =================================================

  sensors_event_t a;
  sensors_event_t g;
  sensors_event_t temp_mpu;

  mpu.getEvent(&a, &g, &temp_mpu);

  float totalAcceleration =
      sqrt(
        pow(a.acceleration.x, 2) +
        pow(a.acceleration.y, 2) +
        pow(a.acceleration.z, 2)
      );


  // =================================================
  // READ TAMPER SWITCH
  // =================================================

  bool isTampered =
      (digitalRead(TAMPER_PIN) == HIGH);


  // =================================================
  // BUILD JSON
  // =================================================

  String jsonPayload =
      "{"
      "\"shipment_id\":\"" + String(shipmentId) + "\","
      "\"temperature\":" + String(temperature, 2) + ","
      "\"humidity\":" + String(humidity, 2) + ","
      "\"acceleration\":" + String(totalAcceleration, 2) + ","
      "\"tamper_status\":" + String(isTampered ? 1 : 0)
      "}";


  Serial.println();
  Serial.println("--------------------------------");
  Serial.println("Sending telemetry...");
  Serial.println(jsonPayload);


  // =================================================
  // HTTP POST
  // =================================================

  HTTPClient http;

  http.begin(serverUrl);

  http.addHeader(
      "Content-Type",
      "application/json"
  );

  int httpResponseCode =
      http.POST(jsonPayload);


  // =================================================
  // RESPONSE
  // =================================================

  if (httpResponseCode > 0) {

    Serial.print("HTTP Response Code: ");
    Serial.println(httpResponseCode);

    String response =
        http.getString();

    Serial.println("Backend response:");
    Serial.println(response);

  } else {

    Serial.print("HTTP request failed: ");
    Serial.println(httpResponseCode);
  }


  http.end();


  // =================================================
  // WAIT
  // =================================================

  delay(3000);
}