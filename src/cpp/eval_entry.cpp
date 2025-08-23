#include "eval.hpp"

PYBIND11_MODULE(eval, module) { module.def("evaluate", &evaluate); }