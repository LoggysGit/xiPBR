#pragma once

// STRUCT FOR *SENDING* //
struct TelemetryPacket {
    uint16_t    temp_in_100;        // Current liquid temperature (* 100)
    uint8_t     ph_10;              // pH value (* 10)
    uint16_t    turbidity_ntu_100;  // Raw turbidity (* 100)
    bool        water_level_ok;     // Water level
    // System
    uint32_t    uptime_sec;         // Time since enabled
    uint8_t     state_code;         // Machine state code (reserved)
};

// STRUCT FOR *RECIEVING* AND *STORING* //
struct SettingsPacket {
    // Environment settings
    uint16_t    target_temp_100;    // Target liquid temperature (* 100)
    uint8_t     target_ph_10;       // Target pH (* 10) [not used yet]
    uint16_t    volume_ml;          // Volume of solution in milliliters
    uint16_t    solution_heat_cap;  // Solution heat capacity IN J/G*C (for still water it is roughly 4.1)
    uint16_t    harvest_amount_ml;  // Harvest amount in milliliters
    // PWM Settings
    uint8_t     aeration_force;     // Aeration pump force in %
    uint8_t     heater_max_force;   // Heater max forse in %
    uint8_t     lb_brightness;      // Bottom light in %
    uint8_t     ls_brightness;      // Side light in %
    uint8_t     lu_brightness;      // Upper light in %
    // Daycycle settings
    uint8_t     hours_active;       // Day schedule (hours active)
    uint8_t     light_fade_sec;     // Light fade (in/out) duration in seconds
    uint8_t     heater_fade_sec;    // Heater fade (on/off) duration in seconds
    uint16_t    aeration_force_n;   // Aeration pump force while inactive mode (night)
};
