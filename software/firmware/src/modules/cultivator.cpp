#include "cultivator.h"

Cultivator::Cultivator(TelemetryPacket& telemetry)
    : telemetry_(telemetry),
      initialized_(false),
      current_daynight_mode_(1),
      last_30m_ms_(0),
      last_12h_ms_(0) {}

bool Cultivator::init() {
    // Set pins
    pinMode(TEMP_SENSOR_PIN, INPUT);
    pinMode(PH_SENSOR_PIN, INPUT);
    pinMode(WL_SENSOR_PIN, INPUT);

    pinMode(HEATER_MOS_PIN, OUTPUT);
    pinMode(LB_PIN, OUTPUT);
    pinMode(LS_PIN, OUTPUT);
    pinMode(LU_PIN, OUTPUT);
    pinMode(PH_MOTOR_PIN, OUTPUT);

    digitalWrite(HEATER_MOS_PIN, LOW);
    digitalWrite(PH_MOTOR_PIN, LOW);

    // Init timers
    const uint32_t now_ms = millis();
    last_30m_ms_ = now_ms;
    last_12h_ms_ = now_ms;
    initialized_ = true;

    // Init sensors and wires

    return true;
}

void Cultivator::tick() {
    if (!initialized_) return;

    const uint32_t now_ms = millis();

    // Execute 12h cycle tick
    if (static_cast<uint32_t>(now_ms - last_12h_ms_) >= TWELVE_HOUR_INTERVAL_MS) {
        last_12h_ms_ = now_ms;
        runTwelveHourTasks(now_ms);
    }

    // Execute 30m cycle tick
    if (static_cast<uint32_t>(now_ms - last_30m_ms_) >= THIRTY_MIN_INTERVAL_MS) {
        last_30m_ms_ = now_ms;
        runThirtyMinuteTasks(now_ms);
    }

    // Read time
}

bool Cultivator::harvest() {
    if (!initialized_) return false;

    // TODO
    return false;
}

void Cultivator::runThirtyMinuteTasks(uint32_t now_ms) {
    // Control temperature
    const float temp_c = readTemperatureC();
    // IF temp IS LOWER THAN REQUIRED VALUE, ENABLE A CYCLE WITH A HEATER AND 30-SEC TEMP RECHECK, UNTIL WE REACH THE MINIMUM +3C

    // Process water level
    const bool water_ok = readWaterLevel();

    triggerTelemetry();
}

void Cultivator::runTwelveHourTasks(uint32_t now_ms) {
    // Read turbidity
    const uint16_t turbidity = readRawTurbidity();

    // Read pH
    const float ph = readPH();
}

void Cultivator::updatePhotoperiod(bool is_night) {
    const uint8_t target_mode = is_night ? 0 : 1;
    if (target_mode == current_daynight_mode_) return;

    current_daynight_mode_ = target_mode;

    if (is_night) {
        smoothLightTransition(false);
        // TODO
        setBubblingLevel(0);
    } else {
        // TODO
        setBubblingLevel(0);
        smoothLightTransition(true);
    }
}

uint16_t Cultivator::readRawTurbidity() {
    // TODO
    return 0;
}

float Cultivator::readPH() {
    // TODO
    return 0.0f;
}

float Cultivator::readTemperatureC() {
    // TODO
    return 0.0f;
}

bool Cultivator::readWaterLevel() {
    // TODO
    return false;
}

void Cultivator::setHeaterState(bool enabled) {
    digitalWrite(HEATER_MOS_PIN, enabled ? HIGH : LOW);
}

void Cultivator::setBubblingLevel(uint8_t level_percent) {
    // TODO
}

void Cultivator::smoothLightTransition(bool turn_on) {
    // TODO
}

void Cultivator::triggerTelemetry() {
    // TODO
}

uint16_t Cultivator::medianFilter(const uint16_t* values, size_t count) {
    if (values == nullptr || count == 0) return 0;

    const size_t n = (count > MEDIAN_MAX_SAMPLES) ? MEDIAN_MAX_SAMPLES : count;
    uint16_t buf[MEDIAN_MAX_SAMPLES] = {0};
    std::memcpy(buf, values, n * sizeof(uint16_t));

    for (size_t i = 1; i < n; ++i) {
        const uint16_t key = buf[i];
        size_t j = i;
        while (j > 0 && buf[j - 1] > key) {
            buf[j] = buf[j - 1];
            --j;
        }
        buf[j] = key;
    }

    if (n % 2 == 1) return buf[n / 2];
    return static_cast<uint16_t>((static_cast<uint32_t>(buf[n / 2 - 1]) + static_cast<uint32_t>(buf[n / 2])) / 2U);
}