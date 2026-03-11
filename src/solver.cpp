#include "solver.hpp"

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iomanip>
#include <limits>
#include <sstream>
#include <stdexcept>

namespace {

using State = std::vector<double>;
using Derivative = std::function<State(double, const State&)>;

constexpr double kRungeKuttaOrder = 4.0;

struct Rk4StepOutput {
    State yNext;
};

struct IntegrationContext {
    Derivative f;
    std::function<double(double)> exact;
    bool hasExact = false;
    std::string name;
};

double trimToBoundary(double x, double h, double b) {
    if (x + h > b) {
        return b - x;
    }
    return h;
}

State addScaled(const State& a, const State& b, double scale) {
    State out(a.size(), 0.0);
    for (size_t i = 0; i < a.size(); ++i) {
        out[i] = a[i] + scale * b[i];
    }
    return out;
}

State combineRK4(const State& y, const State& k1, const State& k2, const State& k3, const State& k4, double h) {
    State out(y.size(), 0.0);
    for (size_t i = 0; i < y.size(); ++i) {
        out[i] = y[i] + h * (k1[i] + 2.0 * k2[i] + 2.0 * k3[i] + k4[i]) / 6.0;
    }
    return out;
}

Rk4StepOutput rk4Step(const Derivative& f, double x, const State& y, double h) {
    const State k1 = f(x, y);
    const State y2 = addScaled(y, k1, h / 2.0);
    const State k2 = f(x + h / 2.0, y2);

    const State y3 = addScaled(y, k2, h / 2.0);
    const State k3 = f(x + h / 2.0, y3);

    const State y4 = addScaled(y, k3, h);
    const State k4 = f(x + h, y4);

    return {combineRK4(y, k1, k2, k3, k4, h)};
}

double maxAbsDiff(const State& a, const State& b) {
    double m = 0.0;
    for (size_t i = 0; i < a.size(); ++i) {
        m = std::max(m, std::abs(a[i] - b[i]));
    }
    return m;
}

State vecDiff(const State& a, const State& b) {
    State out(a.size(), 0.0);
    for (size_t i = 0; i < a.size(); ++i) {
        out[i] = a[i] - b[i];
    }
    return out;
}

double estimateOLP(const State& yH, const State& yH2) {
    const double factor = 1.0 / (std::pow(2.0, kRungeKuttaOrder) - 1.0);
    return factor * maxAbsDiff(yH2, yH);
}

double doublingThreshold(double eps) {
    return eps / std::pow(2.0, kRungeKuttaOrder + 1.0);
}

double initialLambdaForVariant(int variant) {
    const double sign = (variant % 2 == 0) ? 1.0 : -1.0;
    return sign * static_cast<double>(variant) / 2.0;
}

std::string toJsonArray(const State& s) {
    std::ostringstream oss;
    oss << "[";
    for (size_t i = 0; i < s.size(); ++i) {
        if (i > 0) {
            oss << ",";
        }
        oss << std::setprecision(16) << s[i];
    }
    oss << "]";
    return oss.str();
}

std::string readTextFile(const std::string& path) {
    std::ifstream in(path);
    if (!in) {
        throw std::runtime_error("Cannot open input file: " + path);
    }
    std::ostringstream ss;
    ss << in.rdbuf();
    return ss.str();
}

double parseNumber(const std::string& text, const std::string& key, double fallback) {
    const std::string needle = "\"" + key + "\"";
    size_t p = text.find(needle);
    if (p == std::string::npos) {
        return fallback;
    }
    p = text.find(':', p);
    if (p == std::string::npos) {
        return fallback;
    }
    ++p;
    while (p < text.size() && std::isspace(static_cast<unsigned char>(text[p]))) {
        ++p;
    }

    size_t end = p;
    while (end < text.size()) {
        const char ch = text[end];
        if (!(std::isdigit(static_cast<unsigned char>(ch)) || ch == '.' || ch == '-' || ch == '+' || ch == 'e' || ch == 'E')) {
            break;
        }
        ++end;
    }
    if (end == p) {
        return fallback;
    }
    return std::stod(text.substr(p, end - p));
}

int parseInt(const std::string& text, const std::string& key, int fallback) {
    return static_cast<int>(std::llround(parseNumber(text, key, static_cast<double>(fallback))));
}

bool parseBool(const std::string& text, const std::string& key, bool fallback) {
    const std::string needle = "\"" + key + "\"";
    size_t p = text.find(needle);
    if (p == std::string::npos) {
        return fallback;
    }
    p = text.find(':', p);
    if (p == std::string::npos) {
        return fallback;
    }
    ++p;
    while (p < text.size() && std::isspace(static_cast<unsigned char>(text[p]))) {
        ++p;
    }
    if (text.compare(p, 4, "true") == 0) {
        return true;
    }
    if (text.compare(p, 5, "false") == 0) {
        return false;
    }
    return fallback;
}

std::vector<double> parseArray(const std::string& text, const std::string& key, const std::vector<double>& fallback) {
    const std::string needle = "\"" + key + "\"";
    size_t p = text.find(needle);
    if (p == std::string::npos) {
        return fallback;
    }
    p = text.find('[', p);
    if (p == std::string::npos) {
        return fallback;
    }
    size_t end = text.find(']', p);
    if (end == std::string::npos || end <= p + 1) {
        return fallback;
    }

    std::vector<double> out;
    std::string segment = text.substr(p + 1, end - p - 1);
    std::stringstream ss(segment);
    std::string token;
    while (std::getline(ss, token, ',')) {
        std::stringstream ts(token);
        double value = 0.0;
        ts >> value;
        if (!ts.fail()) {
            out.push_back(value);
        }
    }
    if (out.empty()) {
        return fallback;
    }
    return out;
}

IntegrationResult integrateGeneric(const IntegrationContext& context, const State& y0, const IntegrationSettings& settings) {
    IntegrationResult result;
    result.problemName = context.name;

    double x = settings.x0;
    State y = y0;
    double h = settings.h0;
    int c1Total = 0;
    int c2Total = 0;

    result.summary.maxH = std::numeric_limits<double>::lowest();
    result.summary.minH = std::numeric_limits<double>::max();

    StepRow initialRow;
    initialRow.i = 0;
    initialRow.x = settings.x0;
    initialRow.v = y0;
    initialRow.v2 = y0;
    initialRow.delta = State(y0.size(), 0.0);
    initialRow.olp = 0.0;
    initialRow.h = 0.0;
    initialRow.c1 = 0;
    initialRow.c2 = 0;

    if (context.hasExact) {
        initialRow.uExact = context.exact(settings.x0);
        initialRow.absExactError = std::abs(initialRow.uExact - initialRow.v[0]);
        result.summary.maxAbsExactError = initialRow.absExactError;
        result.summary.xAtMaxAbsExactError = settings.x0;
    }

    result.rows.push_back(initialRow);

    int acceptedSteps = 0;
    for (int iter = 0; iter < settings.nmax; ++iter) {
        if (x >= settings.b) {
            break;
        }
        if (h <= 0.0) {
            break;
        }
        h = trimToBoundary(x, h, settings.b);

        int c1 = 0;
        int c2 = 0;
        State yH;
        State yH2;
        double olp = 0.0;
        double stepUsed = h;
        double nextH = h;

        if (!settings.adaptive) {
            yH = rk4Step(context.f, x, y, stepUsed).yNext;
            const State half1 = rk4Step(context.f, x, y, stepUsed / 2.0).yNext;
            yH2 = rk4Step(context.f, x + stepUsed / 2.0, half1, stepUsed / 2.0).yNext;
            olp = estimateOLP(yH, yH2);
        } else {
            while (true) {
                stepUsed = h;
                yH = rk4Step(context.f, x, y, stepUsed).yNext;
                const State half1 = rk4Step(context.f, x, y, stepUsed / 2.0).yNext;
                yH2 = rk4Step(context.f, x + stepUsed / 2.0, half1, stepUsed / 2.0).yNext;
                olp = estimateOLP(yH, yH2);

                if (olp > settings.eps && stepUsed > 1e-12) {
                    h = trimToBoundary(x, stepUsed / 2.0, settings.b);
                    ++c1;
                    ++c1Total;
                    continue;
                }

                nextH = stepUsed;
                if (olp < doublingThreshold(settings.eps) && x + 2.0 * stepUsed <= settings.b) {
                    ++c2;
                    ++c2Total;
                    nextH = 2.0 * stepUsed;
                }
                break;
            }
        }

        const double xNext = x + stepUsed;
        const State yNext = yH;
        const State delta = vecDiff(yH, yH2);

        StepRow row;
        row.i = acceptedSteps + 1;
        row.x = xNext;
        row.v = yH;
        row.v2 = yH2;
        row.delta = delta;
        row.olp = olp;
        row.h = stepUsed;
        row.c1 = c1;
        row.c2 = c2;

        if (context.hasExact) {
            row.uExact = context.exact(xNext);
            row.absExactError = std::abs(row.uExact - row.v[0]);
            if (row.absExactError > result.summary.maxAbsExactError) {
                result.summary.maxAbsExactError = row.absExactError;
                result.summary.xAtMaxAbsExactError = xNext;
            }
        }

        result.rows.push_back(row);

        result.summary.maxAbsOLP = std::max(result.summary.maxAbsOLP, std::abs(olp));
        if (stepUsed > result.summary.maxH) {
            result.summary.maxH = stepUsed;
            result.summary.xAtMaxH = xNext;
        }
        if (stepUsed < result.summary.minH) {
            result.summary.minH = stepUsed;
            result.summary.xAtMinH = xNext;
        }

        x = xNext;
        y = yNext;
        h = nextH;
        ++acceptedSteps;
    }

    result.summary.n = acceptedSteps;
    result.summary.bMinusXn = settings.b - x;
    result.summary.totalDivisions = c1Total;
    result.summary.totalDoublings = c2Total;

    if (acceptedSteps == 0) {
        result.summary.maxH = 0.0;
        result.summary.minH = 0.0;
    }
    return result;
}

void writeOneCsv(const std::filesystem::path& filePath, const IntegrationResult& r, bool includeExact) {
    std::ofstream out(filePath);
    if (!out) {
        throw std::runtime_error("Cannot open file for CSV writing: " + filePath.string());
    }

    if (includeExact) {
        out << "i,xi,vi,v2i,vi_minus_v2i,OLP,hi,C1,C2,ui,abs_ui_minus_vi\n";
    } else {
        out << "i,xi,vi,v2i,vi_minus_v2i,OLP,hi,C1,C2\n";
    }

    out << std::setprecision(12);
    for (const StepRow& row : r.rows) {
        const double vi = row.v.empty() ? 0.0 : row.v[0];
        const double v2i = row.v2.empty() ? 0.0 : row.v2[0];
        const double d = row.delta.empty() ? 0.0 : row.delta[0];

        out << row.i << ","
            << row.x << ","
            << vi << ","
            << v2i << ","
            << d << ","
            << row.olp << ","
            << row.h << ","
            << row.c1 << ","
            << row.c2;

        if (includeExact) {
            out << "," << row.uExact << "," << row.absExactError;
        }
        out << "\n";
    }
}

std::string escapeJson(const std::string& s) {
    std::string out;
    out.reserve(s.size());
    for (char ch : s) {
        if (ch == '\\') {
            out += "\\\\";
        } else if (ch == '"') {
            out += "\\\"";
        } else if (ch == '\n') {
            out += "\\n";
        } else {
            out += ch;
        }
    }
    return out;
}

void writeOneResultJson(std::ostream& out, const IntegrationResult& r, bool includeExact) {
    out << "{\n";
    out << "\"problemName\":\"" << escapeJson(r.problemName) << "\",\n";
    out << "\"summary\":{"
        << "\"n\":" << r.summary.n << ","
        << "\"bMinusXn\":" << std::setprecision(16) << r.summary.bMinusXn << ","
        << "\"maxAbsOLP\":" << r.summary.maxAbsOLP << ","
        << "\"totalDoublings\":" << r.summary.totalDoublings << ","
        << "\"totalDivisions\":" << r.summary.totalDivisions << ","
        << "\"maxH\":" << r.summary.maxH << ","
        << "\"xAtMaxH\":" << r.summary.xAtMaxH << ","
        << "\"minH\":" << r.summary.minH << ","
        << "\"xAtMinH\":" << r.summary.xAtMinH << ","
        << "\"maxAbsExactError\":" << r.summary.maxAbsExactError << ","
        << "\"xAtMaxAbsExactError\":" << r.summary.xAtMaxAbsExactError
        << "},\n";

    out << "\"rows\":[\n";
    for (size_t i = 0; i < r.rows.size(); ++i) {
        const StepRow& row = r.rows[i];
        out << "{";
        out << "\"i\":" << row.i << ","
            << "\"x\":" << std::setprecision(16) << row.x << ","
            << "\"v\":" << toJsonArray(row.v) << ","
            << "\"v2\":" << toJsonArray(row.v2) << ","
            << "\"delta\":" << toJsonArray(row.delta) << ","
            << "\"olp\":" << row.olp << ","
            << "\"h\":" << row.h << ","
            << "\"c1\":" << row.c1 << ","
            << "\"c2\":" << row.c2;
        if (includeExact) {
            out << ",\"uExact\":" << row.uExact << ",\"absExactError\":" << row.absExactError;
        }
        out << "}";
        if (i + 1 < r.rows.size()) {
            out << ",";
        }
        out << "\n";
    }
    out << "]\n";
    out << "}";
}

} // namespace

InputData parseInputJson(const std::string& path) {
    const std::string text = readTextFile(path);

    InputData input;
    input.settings.x0 = parseNumber(text, "x0", input.settings.x0);
    input.settings.b = parseNumber(text, "b", input.settings.b);
    input.settings.h0 = parseNumber(text, "h0", input.settings.h0);
    input.settings.eps = parseNumber(text, "eps", input.settings.eps);
    input.settings.nmax = parseInt(text, "nmax", input.settings.nmax);
    input.settings.adaptive = parseBool(text, "adaptive", input.settings.adaptive);

    input.testProblem.variant = parseInt(text, "variant", input.testProblem.variant);
    input.testProblem.u0 = parseNumber(text, "test_u0", input.testProblem.u0);

    input.mainProblem.m = parseNumber(text, "m", input.mainProblem.m);
    input.mainProblem.c = parseNumber(text, "c", input.mainProblem.c);
    input.mainProblem.k = parseNumber(text, "k", input.mainProblem.k);
    input.mainProblem.kStar = parseNumber(text, "kStar", input.mainProblem.kStar);
    input.mainProblem.u0 = parseNumber(text, "u0", input.mainProblem.u0);
    input.mainProblem.du0 = parseNumber(text, "du0", input.mainProblem.du0);

    input.experiments.kStarValues = parseArray(text, "kStarValues", {0.0, input.mainProblem.kStar});
    input.experiments.cValues = parseArray(text, "cValues", {0.0, input.mainProblem.c});

    if (input.settings.b <= input.settings.x0) {
        throw std::runtime_error("Invalid integration interval: b must be greater than x0");
    }
    if (input.settings.h0 <= 0.0) {
        throw std::runtime_error("Initial step h0 must be positive");
    }
    if (input.settings.nmax <= 0) {
        throw std::runtime_error("nmax must be positive");
    }
    return input;
}

IntegrationResult solveTestProblem(const TestProblemParams& params, const IntegrationSettings& settings) {
    const double lambda = initialLambdaForVariant(params.variant);
    IntegrationContext context;
    context.name = "test_problem";
    context.hasExact = true;
    context.f = [lambda](double /*x*/, const State& y) {
        return State{lambda * y[0]};
    };
    context.exact = [lambda, params](double x) {
        return params.u0 * std::exp(lambda * x);
    };

    return integrateGeneric(context, State{params.u0}, settings);
}

IntegrationResult solveMainProblem(const MainProblemParams& params, const IntegrationSettings& settings) {
    IntegrationContext context;
    context.name = "main_problem";
    context.hasExact = false;

    context.f = [params](double /*x*/, const State& y) {
        const double u = y[0];
        const double du = y[1];

        const double ddu = -(params.c / params.m) * du - (params.k / params.m) * u - (params.kStar / params.m) * u * u * u;
        return State{du, ddu};
    };

    return integrateGeneric(context, State{params.u0, params.du0}, settings);
}

std::vector<IntegrationResult> runMainProblemExperiments(
    const MainProblemParams& baseParams,
    const IntegrationSettings& settings,
    const ExperimentSettings& experiments) {

    std::vector<IntegrationResult> out;

    for (double kStarValue : experiments.kStarValues) {
        MainProblemParams p = baseParams;
        p.kStar = kStarValue;
        IntegrationResult r = solveMainProblem(p, settings);
        r.problemName = "main_problem_kStar_" + std::to_string(kStarValue);
        out.push_back(r);
    }

    for (double cValue : experiments.cValues) {
        MainProblemParams p = baseParams;
        p.c = cValue;
        IntegrationResult r = solveMainProblem(p, settings);
        r.problemName = "main_problem_c_" + std::to_string(cValue);
        out.push_back(r);
    }

    return out;
}

void writeResultJson(
    const std::string& outputPath,
    const IntegrationResult& test,
    const IntegrationResult& main,
    const std::vector<IntegrationResult>& experiments,
    const InputData& input) {

    std::ofstream out(outputPath);
    if (!out) {
        throw std::runtime_error("Cannot open output file: " + outputPath);
    }

    out << "{\n";
    out << "\"input\":{"
        << "\"x0\":" << input.settings.x0 << ","
        << "\"b\":" << input.settings.b << ","
        << "\"h0\":" << input.settings.h0 << ","
        << "\"eps\":" << input.settings.eps << ","
        << "\"nmax\":" << input.settings.nmax << ","
        << "\"adaptive\":" << (input.settings.adaptive ? "true" : "false")
        << "},\n";

    out << "\"test\":";
    writeOneResultJson(out, test, true);
    out << ",\n";

    out << "\"main\":";
    writeOneResultJson(out, main, false);
    out << ",\n";

    out << "\"experiments\":[\n";
    for (size_t i = 0; i < experiments.size(); ++i) {
        writeOneResultJson(out, experiments[i], false);
        if (i + 1 < experiments.size()) {
            out << ",";
        }
        out << "\n";
    }
    out << "]\n";

    out << "}\n";
}

void writeCsvTables(const std::string& outDir, const IntegrationResult& test, const IntegrationResult& main) {
    std::filesystem::create_directories(outDir);
    writeOneCsv(std::filesystem::path(outDir) / "table1_test.csv", test, true);
    writeOneCsv(std::filesystem::path(outDir) / "table2_main.csv", main, false);
}
