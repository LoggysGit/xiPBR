#include <Arduino.h>

#include "config.h"
#include "packets.h"
#include "bridge.h"
#include "cultivator.h"

SettingsPacket pbr_settings;

DataBridge dataBridge(pbr_settings);
Cultivator cultivator();

void setup() {

}

void loop() {

}
