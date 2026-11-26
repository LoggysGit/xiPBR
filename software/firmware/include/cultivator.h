#pragma once

#include <Arduino.h>
#include <cstddef>
#include <cstdint>

#include "config.h"
#include "packets.h"

class Cultivator {
public:
    explicit Cultivator(TelemetryPacket& telemetry);

    bool init();
    void tick();
    bool harvest();

private:
    // Timer branches
    void runThirtyMinuteTasks(uint32_t now_ms);
    void runTwelveHourTasks(uint32_t now_ms);
    void updatePhotoperiod(bool is_night);

    // Readers
    uint16_t readRawTurbidity();
    float readPH();
    float readTemperatureC();
    bool readWaterLevel();

    // Setters
    void setHeaterState(bool enabled);
    void setBubblingLevel(uint8_t level_percent);
    void smoothLightTransition(bool turn_on);

    //void doseAcid(float volume_ml);   // IN FUTURE
    //void doseBase(float volume_ml);   // IN FUTURE

    void triggerTelemetry();

    // Inner math & processing
    static uint16_t medianFilter(const uint16_t* values, size_t count);
    //uint16_t calculateRequiredABDose();   // IN FUTURE

private:
    TelemetryPacket& telemetry_;

    bool initialized_ = false;
    uint8_t current_daynight_mode_ = 1; // 0 - Night, 1 - Day

    uint32_t last_30m_ms_ = 0;
    uint32_t last_12h_ms_ = 0;
};