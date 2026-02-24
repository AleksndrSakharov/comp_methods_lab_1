#include "solver.hpp"

#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>

int main(int argc, char** argv) {
    try {
        if (argc < 3) {
            std::cerr << "Usage: lab1_solver <input.json> <output_dir>\n";
            return 1;
        }

        const std::string inputPath = argv[1];
        const std::string outputDir = argv[2];

        std::filesystem::create_directories(outputDir);

        const InputData input = parseInputJson(inputPath);
        const IntegrationResult test = solveTestProblem(input.testProblem, input.settings);
        const IntegrationResult main = solveMainProblem(input.mainProblem, input.settings);
        const std::vector<IntegrationResult> experiments =
            runMainProblemExperiments(input.mainProblem, input.settings, input.experiments);

        writeCsvTables(outputDir, test, main);
        writeResultJson((std::filesystem::path(outputDir) / "result.json").string(), test, main, experiments, input);

        std::cout << "Completed. Output written to: " << outputDir << "\n";
        std::cout << "Steps (test): " << test.summary.n << ", max|OLP|=" << test.summary.maxAbsOLP << "\n";
        std::cout << "Steps (main): " << main.summary.n << ", max|OLP|=" << main.summary.maxAbsOLP << "\n";
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "Error: " << ex.what() << "\n";
        return 2;
    }
}
