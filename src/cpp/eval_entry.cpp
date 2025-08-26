#include "eval.hpp"

namespace eval2048 {

PYBIND11_MODULE(eval, module) { module.def("evaluate", &evaluate); }

}