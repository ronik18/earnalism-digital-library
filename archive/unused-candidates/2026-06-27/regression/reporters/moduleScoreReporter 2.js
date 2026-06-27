const reportUtils = require("../utils/report");

class ModuleScoreReporter {
  onRunComplete(_, results) {
    this.report = reportUtils.buildModuleReport(results);
    reportUtils.writeReport(this.report);
    const lines = this.report.modules
      .map((row) => `${row.score === 100 ? "PASS" : "FAIL"} ${row.score.toFixed(2)} ${row.moduleName}`)
      .join("\n");
    process.stdout.write(`\nRegression module scores\n${lines}\n`);
    if (!this.report.pass) {
      this.error = new Error(`Regression gate failed: ${this.report.mandatoryFailures.join(", ")}`);
    }
  }

  getLastError() {
    return this.error;
  }
}

module.exports = ModuleScoreReporter;
