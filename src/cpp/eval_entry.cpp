#include "eval.hpp"

PYBIND11_MODULE(eval, module) {
    pybind11::enum_<eval2048::Move>(module, "Move")
        .value("UP", eval2048::Move::UP)
        .value("DOWN", eval2048::Move::DOWN)
        .value("LEFT", eval2048::Move::LEFT)
        .value("RIGHT", eval2048::Move::RIGHT)
        .value("NONE", eval2048::Move::NONE);
    pybind11::enum_<eval2048::Evaluation>(module, "Evaluation")
        .value("AUTO", eval2048::Evaluation::AUTO)
        .value("MC", eval2048::Evaluation::MC)
        .value("MCTS", eval2048::Evaluation::MCTS)
        .value("EXPMAX", eval2048::Evaluation::EXPMAX);
    module.def("evaluate", &eval2048::evaluate);
}