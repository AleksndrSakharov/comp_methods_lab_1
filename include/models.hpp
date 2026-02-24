#pragma once

#include <string>
#include <vector>

struct IntegrationSettings {
    double x0 = 0.0;
    double b = 1.0;
    double h0 = 0.01;
    double eps = 1e-5;
    int nmax = 100000;
    bool adaptive = false;
};

struct TestProblemParams {
    int variant = 25;
    double u0 = 1.0;
};

struct MainProblemParams {
    double m = 0.01;
    double c = 0.15;
    double k = 2.0;
    double kStar = 2.0;
    double u0 = 10.0;
    double du0 = 0.0;
};

struct StepRow {
    int i = 0;
    double x = 0.0;
    std::vector<double> v;
    std::vector<double> v2;
    std::vector<double> delta;
    double olp = 0.0;
    double h = 0.0;
    int c1 = 0;
    int c2 = 0;
    double uExact = 0.0;
    double absExactError = 0.0;
};

struct IntegrationSummary {
    int n = 0;
    double bMinusXn = 0.0;
    double maxAbsOLP = 0.0;
    int totalDoublings = 0;
    int totalDivisions = 0;
    double maxH = 0.0;
    double xAtMaxH = 0.0;
    double minH = 0.0;
    double xAtMinH = 0.0;
    double maxAbsExactError = 0.0;
    double xAtMaxAbsExactError = 0.0;
};

struct IntegrationResult {
    std::string problemName;
    std::vector<StepRow> rows;
    IntegrationSummary summary;
};

struct ExperimentSettings {
    std::vector<double> kStarValues;
    std::vector<double> cValues;
};

struct InputData {
    IntegrationSettings settings;
    TestProblemParams testProblem;
    MainProblemParams mainProblem;
    ExperimentSettings experiments;
};
