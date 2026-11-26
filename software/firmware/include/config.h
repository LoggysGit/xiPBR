#pragma once

// PINOUT //
#define TEMP_SENSOR_PIN 0
#define PH_SENSOR_PIN   0
#define WL_SENSOR_PIN   0

#define HEATER_MOS_PIN  0
#define LB_PIN          0
#define LS_PIN          0
#define LU_PIN          0

#define PH_MOTOR_PIN    0

// CONFIGURATION //
#define BAUDRATE        115200

#define THIRTY_MIN_INTERVAL_MS  (30UL * 60UL * 1000UL)
#define TWELVE_HOUR_INTERVAL_MS (12UL * 60UL * 60UL * 1000UL)

#define MEDIAN_MAX_SAMPLES      31