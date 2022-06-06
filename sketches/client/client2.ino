#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <ArduinoJson.h>
#include <OneWire.h>
#include <DallasTemperature.h>

#define ONE_WIRE_BUS 0
const int LED_PIN = 16;

const char* ssid     = "polinchek";
const char* password = "122222322";

const char* host = "192.168.43.1";  //Server IP Address here

const char* boardName = "coco";


int interval = 10000;  // Interval between requests

OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature tempSensor(&oneWire);
WiFiClient client;
DynamicJsonDocument doc(2048);
//StaticJsonBuffer<1024> jsonBuffer; // compute via https://arduinojson.org/v5/assistant/

void setup() {
    Serial.begin(115200);
    delay(100);

    // We start by connecting to a WiFi network
    Serial.println();
    Serial.println();
    Serial.print("Connecting to ");
    Serial.println(ssid);

    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);

    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }

    Serial.println("");
    Serial.println("WiFi connected");
    Serial.println("IP address: ");
    Serial.println(WiFi.localIP());

    tempSensor.setResolution(12);

    pinMode(LED_BUILTIN, OUTPUT);
    pinMode(compressor, OUTPUT);
    
    digitalWrite(LED_BUILTIN, 0);
    delay(250);
    digitalWrite(LED_BUILTIN, 1);
    delay(250);
    digitalWrite(LED_BUILTIN, 0);
    delay(250);
    digitalWrite(LED_BUILTIN, 1);
    delay(250);
    digitalWrite(LED_BUILTIN, 0);
    delay(250);
    digitalWrite(LED_BUILTIN, 1);
}


void loop() {
    pinMode(LED_BUILTIN, OUTPUT);
    pinMode(compressor, OUTPUT);
    if (WiFi.status() == WL_CONNECTED) { //Check WiFi connection status
        HTTPClient http;
        http.begin(client, "http://192.168.43.1:8000/interact");   // pass Server IP Address here
        http.addHeader("Content-Type", "application/json");
        String request = getStates();
        Serial.println(request);
        int httpCode = http.POST(request);
        if (httpCode > 0) {
            String payload = http.getString();
            Serial.println(payload);
            deserializeJson(doc, payload);
            http.end();

            digitalWrite(LED_PIN, doc["coco_led"].as<bool>());
        }
        else {
            Serial.println("Unable to request");
        }
    }
  delay(interval);
}


String getStates() {
    float temp1;
    tempSensor.requestTemperatures();
    temp1 = tempSensor.getTempCByIndex(0);
    String json;
    doc["name"] = boardName;

    // Get pin state
    doc["led_temp"] = temp1;
    serializeJson(doc, json);
    return json;
}
