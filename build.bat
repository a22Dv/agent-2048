@echo off

cmake --preset wclang-debug
cmake --build build\debug
copy .\build\debug\eval.cp313-win_amd64.pyd .\src\agent_2048\
cd src
pybind11-stubgen agent_2048.eval -o .
cd ..