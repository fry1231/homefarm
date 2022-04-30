#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <ArduinoJson.h>


const char* ssid     = "phone";
const char* password = "122222322";

const char* host = "192.168.43.1";  //Server IP Address here

const char* boardName = "farm";

char* json;
HTTPClient client;
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
    if (WiFi.status() == WL_CONNECTED) { //Check WiFi connection status
        client.begin("192.168.43.1/interact");   // pass Server IP Address here
        client.addHeader("Content-Type", "application/json");
        client.POST(getState());

        String payload = client.getString();
        Serial.println(payload);

        deserializeJson(doc, client.getStream());

        digitalWrite(LED_BUILTIN, doc["LED"].as<int>());
    }
  delay(500);

}


String getState() {
    doc["name"] = boardName;

    // Get pin state
    doc["state"] = digitalRead(LED_BUILTIN);
    serializeJson(doc, json);
    return json;
}
