@echo off

cmake --preset wclang-debug
cmake --build build\debug
copy .\build\debug\eval.cp313-win_amd64.pyd .\src\agent_2048\

:: Somehow doesn't accept going to src directory via the command
:: so we manually cd there instead.
cd src
pybind11-stubgen agent_2048.eval -o .
cd ..