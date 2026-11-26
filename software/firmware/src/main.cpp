#include <Arduino.h>

#include "config.h"
#include "packets.h"
#include "bridge.h"
#include "cultivator.h"

TelemetryPacket actualTelemetry;
SettingsPacket pbrSettings;

DataBridge dataBridge(pbrSettings);
Cultivator cultivator(actualTelemetry, pbrSettings);

void setup() {
  dataBridge.init();
  if (!cultivator.init()) Serial.println("Cultivator core cannot start");
}

void loop() {
  cultivator.tick();
  dataBridge.tick();
}
