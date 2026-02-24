#pragma once

#include "models.hpp"

#include <string>
#include <vector>

InputData parseInputJson(const std::string& path);

IntegrationResult solveTestProblem(const TestProblemParams& params, const IntegrationSettings& settings);
IntegrationResult solveMainProblem(const MainProblemParams& params, const IntegrationSettings& settings);

std::vector<IntegrationResult> runMainProblemExperiments(
    const MainProblemParams& baseParams,
    const IntegrationSettings& settings,
    const ExperimentSettings& experiments);

void writeResultJson(
    const std::string& outputPath,
    const IntegrationResult& test,
    const IntegrationResult& main,
    const std::vector<IntegrationResult>& experiments,
    const InputData& input);

void writeCsvTables(const std::string& outDir, const IntegrationResult& test, const IntegrationResult& main);
