#pragma once

#include <Arduino.h>

#include "config.h"

class Cultivator{
public:
    Cultivator();

    bool init();

private:
    int a;
};