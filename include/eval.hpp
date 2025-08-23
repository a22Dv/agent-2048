#pragma once

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <cstdint>
#include <vector>

std::uint8_t evaluate(std::vector<std::uint32_t> state, std::uint8_t type);