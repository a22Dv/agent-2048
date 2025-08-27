cmake_minimum_required(VERSION 3.22)

# Somehow crashes without this.
set(CMAKE_PREFIX_PATH "${CMAKE_SOURCE_DIR}/venv")

project(eval CXX)
find_package(pybind11 REQUIRED)
pybind11_add_module(eval "${CMAKE_SOURCE_DIR}/src/cpp/eval.cpp" "${CMAKE_SOURCE_DIR}/src/cpp/eval_entry.cpp")
target_include_directories(
    eval 
    PRIVATE 
    "${CMAKE_SOURCE_DIR}/venv/include" 
    "${CMAKE_SOURCE_DIR}/include"
)

# Increased step limit due to look-up table initialization requiring more steps.
target_compile_options(eval PRIVATE -march=native /EHsc -Xclang -fconstexpr-steps=80000000)
target_compile_features(eval PRIVATE cxx_std_20)