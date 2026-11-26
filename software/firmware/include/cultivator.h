#pragma once

#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>

#include <Arduino.h>

#include "config.h"
#include "packets.h"

class Cultivator {
public:
    explicit Cultivator(TelemetryPacket& telemetry,
                        SettingsPacket& setts);

    bool init();
    void tick();
    bool harvest();

private:
    // Timer branches
    void runThirtyMinuteTasks(uint32_t now_ms);
    void runTwelveHourTasks(uint32_t now_ms);
    void updatePhotoperiod(bool is_night);

    // Sensor readers
    uint16_t readRawTurbidity();
    float readPH();
    float readTemperatureC();
    bool readWaterLevel();

    // Other
    void setHeaterState(bool enabled);
    void startHeaterCurve(uint32_t duration_sec, uint32_t now_ms);
    void stopHeater();
    void updateHeaterCurve(uint32_t now_ms);

    void setBubblingLevel(uint8_t level_percent);

    void smoothLightTransition(bool turn_on);
    void updateLightFade(uint32_t now_ms);

    //void doseAcid(float volume_ml);   // IN FUTURE
    //void doseBase(float volume_ml);   // IN FUTURE

    void triggerTelemetry();

    // Inner math & processing
    static uint16_t medianFilter(const uint16_t* values, size_t count);
    //uint16_t calculateRequiredABDose();   // IN FUTURE

private:
    TelemetryPacket& telemetry_;
    SettingsPacket& setts_;

    bool initialized_ = false;

    uint8_t current_daynight_mode_ = 1; // 0 - Night, 1 - Day

    // Loop timers
    uint32_t last_30m_ms_ = 0;
    uint32_t last_12h_ms_ = 0;

    // Light control variables
    bool light_fading_ = false;
    bool light_fade_target_on_ = false;
    uint32_t light_fade_start_ms_ = 0;
    uint8_t current_light_duty_ = 0;

    // Heater contol variables
    bool heater_active_ = false;
    uint32_t heater_start_ms_ = 0;
    uint32_t heater_duration_ms_ = 0;
    uint16_t current_heater_duty_ = 0;
};