#include "bridge.h"

DataBridge::DataBridge(SettingsPacket& setts,
                       Stream& serial_port,
                       uint32_t baudrate)
    : _pbr_setts(setts),
      _port(serial_port),
      _baudrate(baudrate),
      _rx_index(0),
      _initialized(false),
      _on_command(nullptr) {
    std::memset(_rx_buffer, 0, sizeof(_rx_buffer));
}

bool DataBridge::init() {
    if (&_port == &Serial) Serial.begin(_baudrate);
    else static_cast<HardwareSerial&>(_port).begin(_baudrate);

    Serial.println("[System] xiPBR launched. Initting...");

    _rx_index = 0;
    std::memset(_rx_buffer, 0, sizeof(_rx_buffer));
    _initialized = true;
    return true;
}

bool DataBridge::saveSettings() {
    if (!_initialized) return false;
    return writeSettingsStorage(_pbr_setts);
}

bool DataBridge::loadSettings() {
    if (!_initialized) return false;

    SettingsPacket loaded{};
    if (!readSettingsStorage(loaded)) return false;

    _pbr_setts = loaded;
    return true;
}

void DataBridge::tick() {
    if (!_initialized) return;
    readIncomingLines();
}

bool DataBridge::sendTelemetryData(const TelemetryPacket& packet) {
    if (!_initialized) return false;

    // TODO
    return false;
}

void DataBridge::setCommandCallback(CommandCallback cb) {
    _on_command = std::move(cb);
}

void DataBridge::readIncomingLines() {
    while (_port.available() > 0) {
        const int raw = _port.read();
        if (raw < 0) break;

        const char ch = static_cast<char>(raw);

        if (ch == '\r') {
            continue;
        }

        if (ch == '\n') {
            _rx_buffer[_rx_index] = '\0';
            if (_rx_index > 0) {
                handleLine(_rx_buffer);
            }
            _rx_index = 0;
            continue;
        }

        if (_rx_index < (RX_BUFFER_SIZE - 1)) {
            _rx_buffer[_rx_index++] = ch;
        }
        else {
            _rx_index = 0;
            std::memset(_rx_buffer, 0, sizeof(_rx_buffer));
        }
    }
}

void DataBridge::handleLine(const char* line) {
    if (line == nullptr || line[0] == '\0') return;

    JsonDocument doc;
    const DeserializationError err = deserializeJson(doc, line);
    if (err) return;

    if (_on_command) _on_command(doc);
}

bool DataBridge::writeJsonLine(const JsonDocument& doc) {
    if (!_initialized) return false;

    const size_t written = serializeJson(doc, _port);
    if (written == 0) return false;

    return _port.println() > 0;
}

bool DataBridge::writeSettingsStorage(const SettingsPacket& data) {
    // TODO
    return false;
}

bool DataBridge::readSettingsStorage(SettingsPacket& out_data) {
    // TODO
    return false;
}