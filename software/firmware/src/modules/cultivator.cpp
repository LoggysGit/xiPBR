#include "cultivator.h"

Cultivator::Cultivator(TelemetryPacket& telemetry, SettingsPacket& setts, DataBridge& dataBridge)
    : telemetry_(telemetry),
      setts_(setts),
      bridgeObjRef_(dataBridge),

      initialized_(false),
      current_daynight_mode_(1),

      last_30m_ms_(0),
      last_12h_ms_(0),
      light_fading_(false),
      light_fade_target_on_(false),
      light_fade_start_ms_(0),

      heater_active_(false),
      heater_start_ms_(0),
      heater_duration_ms_(0),
      current_heater_duty_(0) {}

bool Cultivator::init() {
    /* Set pins */
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
    analogWrite(HEATER_MOS_PIN, 0);

    /* Init telemetry defaults */
    telemetry_.temp_in_100 = 0;
    telemetry_.ph_10 = 0;
    telemetry_.turbidity_ntu_100 = 0;
    telemetry_.water_level_ok = false;
    telemetry_.uptime_sec = 0;
    telemetry_.state_code = 0;

    /* Init timers */
    const uint32_t now_ms = millis();
    last_30m_ms_ = now_ms;
    last_12h_ms_ = now_ms;
    initialized_ = true;

    /* Init sensors and wires */
    tempSensor_.begin();
    tempSensor_.setResolution(12);

    return true;
}

void Cultivator::tick() {
    if (!initialized_) return;

    const uint32_t now_ms = millis();

    // Update non-blocking PWM transitions
    updateLightFade(now_ms);
    updateHeaterCurve(now_ms);

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
    // - (ds3231)
}

bool Cultivator::harvest() {
    if (!initialized_) return false;

    // TODO
    return false;
}

void Cultivator::runThirtyMinuteTasks(uint32_t now_ms) {
    // Process water level first
    const bool water_ok = readWaterLevel();
    telemetry_.water_level_ok = water_ok;

    // Control temperature
    const float temp_c = readTemperatureC();
    const int32_t temp_scaled = static_cast<int32_t>(std::lround(temp_c * 100.0f));
    telemetry_.temp_in_100 = (temp_scaled > 0) ? static_cast<uint16_t>(temp_scaled) : 0U;

    if (!water_ok) {
        stopHeater();
    }
    else {
        const float target_temp = static_cast<float>(setts_.target_temp_100) / 100.0f;
        if (temp_c < target_temp) {
            // t = (c * m * delta_T) / (P * kp) [m ~= V for density ~ 1 g/ml]
            const float delta_t = (target_temp - temp_c) + static_cast<float>(TEMP_INADVANCE);
            if (delta_t > 0.0f && HEATER_POWER > 0.0f) {
                const float joules = static_cast<float>(setts_.solution_heat_cap) *
                                     static_cast<float>(setts_.volume_ml) * delta_t;
                const float kp = static_cast<float>(setts_.heater_max_force) / 100.0f;
                const uint32_t heater_sec = static_cast<uint32_t>(joules / (HEATER_POWER * kp) );
                startHeaterCurve(heater_sec, now_ms);
            }
            else stopHeater();
        }
        else stopHeater();
    }

    triggerTelemetry();
}

void Cultivator::runTwelveHourTasks(uint32_t now_ms) {
    (void)now_ms;

    // Read turbidity
    const uint16_t turbidity = readRawTurbidity();
    telemetry_.turbidity_ntu_100 = turbidity;

    // Read pH
    const float ph = readPH();
    const int32_t ph_scaled = static_cast<int32_t>(std::lround(ph * 10.0f));
    if (ph_scaled < 0) {
        telemetry_.ph_10 = 0;
    }
    else if (ph_scaled > 255) {
        telemetry_.ph_10 = 255;
    }
    else {
        telemetry_.ph_10 = static_cast<uint8_t>(ph_scaled);
    }
}

/* --- SENSOR READ FUNCTIONS --- */
uint16_t Cultivator::readRawTurbidity() {
    // TODO
    return 0;
}

float Cultivator::readPH() {
    // TODO
    return 0.0f;
}

float Cultivator::readTemperatureC() {
    uint16_t samples_x100[MEDIAN_MAX_SAMPLES] = {0};
    size_t valid_count = 0;

    for (size_t i = 0; i < MEDIAN_MAX_SAMPLES; ++i) {
        tempSensor_.requestTemperatures();
        const float raw_c = tempSensor_.getTempCByIndex(0);

        // Remove errors and corrupted values
        if (raw_c > -55.0f && raw_c < 125.0f) {
            const int32_t scaled = static_cast<int32_t>(std::lround(raw_c * 100.0f));
            if (scaled >= 0 && scaled <= 65535) {
                samples_x100[valid_count++] = static_cast<uint16_t>(scaled);
            }
        }
    }

    if (valid_count == 0) return 0;

    const uint16_t filtered_x100 = medianFilter(samples_x100, valid_count);
    return static_cast<float>(filtered_x100) / 100.0f;
}

bool Cultivator::readWaterLevel() {
    // TODO
    return false;
}

/* --- HEATER CONTROL FUNCTIONS --- */
void Cultivator::setHeaterState(bool enabled) {
    if (!enabled) {
        stopHeater();
        return;
    }
    const uint16_t peak_duty = static_cast<uint16_t>(
        (static_cast<uint32_t>(PWM_MAX_DUTY) * setts_.heater_max_force) / 100U
    );
    current_heater_duty_ = peak_duty;
    analogWrite(HEATER_MOS_PIN, current_heater_duty_);
}
void Cultivator::startHeaterCurve(uint32_t duration_sec, uint32_t now_ms) {
    if (duration_sec == 0) {
        stopHeater();
        return;
    }
    heater_active_ = true;
    heater_start_ms_ = now_ms;
    heater_duration_ms_ = duration_sec * 1000UL;
}
void Cultivator::stopHeater() {
    heater_active_ = false;
    heater_duration_ms_ = 0;
    current_heater_duty_ = 0;
    analogWrite(HEATER_MOS_PIN, 0);
}
void Cultivator::updateHeaterCurve(uint32_t now_ms) {
    if (!heater_active_) return;

    const uint32_t elapsed = static_cast<uint32_t>(now_ms - heater_start_ms_);
    if (heater_duration_ms_ == 0 || elapsed >= heater_duration_ms_) {
        stopHeater();
        return;
    }

    const uint16_t peak_duty = static_cast<uint16_t>(
        (static_cast<uint32_t>(PWM_MAX_DUTY) * setts_.heater_max_force) / 100U
    );

    const uint32_t ramp_ms = static_cast<uint32_t>(setts_.heater_fade_sec) * 1000UL;
    const uint32_t half_window_ms = heater_duration_ms_ / 2U;
    const uint32_t effective_ramp_ms = (ramp_ms < half_window_ms) ? ramp_ms : half_window_ms;

    uint16_t duty = peak_duty;
    if (effective_ramp_ms > 0) {
        const uint32_t down_start_ms = heater_duration_ms_ - effective_ramp_ms;
        if (elapsed < effective_ramp_ms) {
            const float up_ratio = static_cast<float>(elapsed) / static_cast<float>(effective_ramp_ms);
            duty = static_cast<uint16_t>(static_cast<float>(peak_duty) * up_ratio);
        } else if (elapsed > down_start_ms) {
            const uint32_t remaining = heater_duration_ms_ - elapsed;
            const float down_ratio = static_cast<float>(remaining) / static_cast<float>(effective_ramp_ms);
            duty = static_cast<uint16_t>(static_cast<float>(peak_duty) * down_ratio);
        }
    }

    current_heater_duty_ = duty;
    analogWrite(HEATER_MOS_PIN, current_heater_duty_);
}

/* --- BUBBLING CONTROL FUNCTIONS --- */
void Cultivator::setBubblingLevel(uint8_t level_percent) {
    // TODO
}

/* --- LIGHT CONTROL FUNCTIONS --- */
void Cultivator::smoothLightTransition(bool turn_on) {
    light_fade_target_on_ = turn_on;
    light_fade_start_ms_ = millis();
    light_fading_ = true;
}
void Cultivator::updateLightFade(uint32_t now_ms) {
    if (!light_fading_) return;

    const uint32_t duration_ms = static_cast<uint32_t>(setts_.light_fade_sec) * 1000UL;

    if (duration_ms == 0) {
        const uint16_t lb = light_fade_target_on_ ? setts_.lb_brightness : 0U;
        const uint16_t ls = light_fade_target_on_ ? setts_.ls_brightness : 0U;
        const uint16_t lu = light_fade_target_on_ ? setts_.lu_brightness : 0U;

        analogWrite(LB_PIN, lb);
        analogWrite(LS_PIN, ls);
        analogWrite(LU_PIN, lu);
        light_fading_ = false;
        return;
    }

    const uint32_t elapsed = static_cast<uint32_t>(now_ms - light_fade_start_ms_);
    float ratio = 0.0f;

    if (elapsed >= duration_ms) {
        ratio = light_fade_target_on_ ? 1.0f : 0.0f;
        light_fading_ = false;
    } else {
        const float raw_progress = static_cast<float>(elapsed) / static_cast<float>(duration_ms);
        ratio = light_fade_target_on_ ? raw_progress : (1.0f - raw_progress);
    }

    const uint16_t lb = static_cast<uint16_t>(static_cast<float>(setts_.lb_brightness) * ratio);
    const uint16_t ls = static_cast<uint16_t>(static_cast<float>(setts_.ls_brightness) * ratio);
    const uint16_t lu = static_cast<uint16_t>(static_cast<float>(setts_.lu_brightness) * ratio);

    analogWrite(LB_PIN, lb);
    analogWrite(LS_PIN, ls);
    analogWrite(LU_PIN, lu);
}

/* --- TELEMETRY SENDING --- */
void Cultivator::triggerTelemetry() {
    telemetry_.uptime_sec = millis() / 1000UL;
    bridgeObjRef_.sendTelemetryData(telemetry_);
}

/* --- INNER MATH & PROCESSING FUNCTIONS --- */
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
