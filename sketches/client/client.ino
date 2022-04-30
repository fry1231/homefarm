#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <ArduinoJson.h>


const char* ssid     = "phone";
const char* password = "122222322";

const char* host = "192.168.43.1";  //Server IP Address here

const char* boardName = "farm";


WiFiClient client;
DynamicJsonDocument doc(1024);
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


    pinMode(LED_BUILTIN, OUTPUT);
}


void loop() {
    pinMode(LED_BUILTIN, OUTPUT);
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
            Serial.println("doc attr: " + doc["LED"].as<String>());
            digitalWrite(LED_BUILTIN, doc["LED"].as<int>());
        }
        else {
            Serial.println("Unable to request");
        }
    }
  delay(500);
}


String getStates() {
    String json;
    doc["name"] = boardName;

    // Get pin state
    doc["LED"] = digitalRead(LED_BUILTIN);
    serializeJson(doc, json);
    return json;
}
