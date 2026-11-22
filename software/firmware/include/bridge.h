#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>
#include <functional>

#include "config.h"
#include "packets.h"

class DataBridge {
public:
    explicit DataBridge(SettingsPacket& setts);

private:
    SettingsPacket& _pbr_setts;
};