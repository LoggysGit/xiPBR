#pragma once

// STRUCT FOR *SENDING* //
struct TelemetryPacket {
    uint16_t    temp_in_100;        // Current liquid temperature (* 100)
    uint8_t     ph_10;              // pH value (* 10)
    uint16_t    turbidity_ntu_100;  // Raw turbidity (* 100)
    bool        water_level_ok;     // Water level
    uint32_t    uptime_sec;         // Time since enabled
    uint8_t     state_code;         // Machine state code (reserved)
};

// STRUCT FOR *RECIEVING* AND *STORING* //
struct SettingsPacket {
    // Constant settings
    uint16_t    target_temp_100;    // Target liquid temperature (* 100)
    uint8_t     target_ph_10;       // Target pH (* 10) [not used yet]
    uint16_t    aeration_force;     // Aeration pump force (PWM)
    uint16_t    lb_brightness;      // Bottom light (PWM)
    uint16_t    ls_brightness;      // Side light (PWM)
    uint16_t    lu_brightness;      // Upper light (PWM)
    // Daycycle settings
    uint8_t     hours_active;       // Day schedule (hours active)
    uint8_t     light_fade_sec;     // Light fade (in/out) duration (in seconds)
    uint16_t    aeration_force_n;   // Aeration pump force while inactive mode (night)
    // Harvest settings
    uint16_t    harvest_amount_ml;  // Harvest amount in milliliters
};