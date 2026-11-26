#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>
#include <cstddef>
#include <cstdint>
#include <functional>

#include "config.h"
#include "packets.h"

class DataBridge {
public:
    using CommandCallback = std::function<void(const JsonDocument& cmd)>;

    explicit DataBridge(SettingsPacket& setts,
                        Stream& serial_port = Serial,
                        uint32_t baudrate = BAUDRATE);

    bool init();

    bool saveSettings();
    bool loadSettings();

    void tick();

    bool sendTelemetryData(const TelemetryPacket& packet);
    void setCommandCallback(CommandCallback cb);

private:
    // Inner functions
    void readIncomingLines();
    void handleLine(const char* line);
    bool writeJsonLine(const JsonDocument& doc);

    // Memory functions
    bool writeSettingsStorage(const SettingsPacket& data);
    bool readSettingsStorage(SettingsPacket& out_data);

private:
    SettingsPacket& _pbr_setts;
    Stream& _port;
    uint32_t _baudrate = 115200;

    static constexpr size_t RX_BUFFER_SIZE = 512;
    char _rx_buffer[RX_BUFFER_SIZE] = {0};
    size_t _rx_index = 0;

    bool _initialized = false;
    CommandCallback _on_command = nullptr;
};