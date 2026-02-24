cmake_minimum_required(VERSION 3.16)
project(comp_methods_lab_1 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(lab1_solver
    src/main.cpp
    src/solver.cpp
)

target_include_directories(lab1_solver PRIVATE include)
