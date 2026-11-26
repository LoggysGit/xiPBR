#include <Arduino.h>

#include "config.h"
#include "packets.h"
#include "bridge.h"
#include "cultivator.h"

TelemetryPacket actualTelemetry;
SettingsPacket pbrSettings;

DataBridge dataBridge(pbrSettings);
Cultivator cultivator(actualTelemetry);

void setup() {
  Serial.begin(BAUDRATE);
  Serial.println("[System] xiPBR launched. Initting...");

  if (!dataBridge.init()) Serial.println("Data bridge cannot start");
  if (!cultivator.init()) Serial.println("Cultivator core cannot start");
}

void loop() {
  cultivator.tick();
  dataBridge.tick();
}
