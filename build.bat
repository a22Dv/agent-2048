@echo off

cmake --preset wclang-release
cmake --build build\release
copy .\build\release\eval.cp313-win_amd64.pyd .\src\agent_2048\
:: copy .\build\release\eval.pdb .\venv\scripts\

:: Somehow doesn't accept going to src directory via the command
:: so we manually cd there instead.
cd src
pybind11-stubgen agent_2048.eval -o .
cd ..