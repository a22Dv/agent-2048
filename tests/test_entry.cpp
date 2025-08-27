#include "eval.hpp"

using namespace eval2048;
int main() {
    State s{0x0002'1000'0002'0002};
    monteCarlo(s);
}