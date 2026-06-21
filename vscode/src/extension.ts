import * as vscode from "vscode";
import { execFile, ExecFileException } from "child_process";

const NETLIST_EXTS = [".cir", ".net", ".sp", ".spice", ".ckt"];

interface Finding {
  severity: string; // FATAL | SILENT | WARN | INFO
  code: string;
  message: string;
}
interface SgResult {
  path: string;
  verdict: string; // TRUSTWORTHY | SUSPECT | FAILED
  returncode: number;
  source: string;
  issues: Finding[];
}

let diagnostics: vscode.DiagnosticCollection;
let output: vscode.OutputChannel;
let warnedMissing = false;

export function activate(context: vscode.ExtensionContext) {
  diagnostics = vscode.languages.createDiagnosticCollection("spiceguard");
  output = vscode.window.createOutputChannel("spiceguard");
  context.subscriptions.push(diagnostics, output);

  context.subscriptions.push(
    vscode.commands.registerCommand("spiceguard.checkFile", () => {
      const ed = vscode.window.activeTextEditor;
      if (ed) {
        check(ed.document, true);
      }
    }),
    vscode.workspace.onDidSaveTextDocument((doc) => check(doc)),
    vscode.workspace.onDidOpenTextDocument((doc) => {
      if (config<boolean>("checkOnOpen", true)) {
        check(doc);
      }
    }),
    vscode.workspace.onDidCloseTextDocument((doc) => diagnostics.delete(doc.uri))
  );

  // Check any already-open netlists on activation.
  vscode.workspace.textDocuments.forEach((doc) => check(doc));
}

export function deactivate() {
  diagnostics?.clear();
}

function config<T>(key: string, def: T): T {
  return vscode.workspace.getConfiguration("spiceguard").get<T>(key, def);
}

function isNetlist(doc: vscode.TextDocument): boolean {
  if (doc.uri.scheme !== "file") {
    return false;
  }
  const p = doc.uri.fsPath.toLowerCase();
  return NETLIST_EXTS.some((e) => p.endsWith(e));
}

function check(doc: vscode.TextDocument, manual = false) {
  if (!config<boolean>("enable", true) || !isNetlist(doc)) {
    return;
  }
  const bin = config<string>("path", "spiceguard");
  const ngspicePath = config<string>("ngspicePath", "");
  const args = ["--json"];
  if (ngspicePath) {
    args.push("--ngspice", ngspicePath);
  }
  args.push(doc.uri.fsPath);

  execFile(bin, args, { timeout: 130000 }, (err, stdout, stderr) => {
    // Exit codes 1 (FAILED) and 2 (SUSPECT) are normal and still emit JSON on
    // stdout; only treat the absence of stdout as a real tooling failure.
    if (!stdout || !stdout.trim()) {
      diagnostics.delete(doc.uri);
      handleNoOutput(err, stderr, bin, manual);
      return;
    }
    let results: SgResult[];
    try {
      results = JSON.parse(stdout);
    } catch (e) {
      output.appendLine("spiceguard: failed to parse --json output:\n" + stdout);
      return;
    }
    applyDiagnostics(doc, results);
    if (manual && results.length > 0) {
      vscode.window.showInformationMessage(
        `spiceguard: ${results[0].verdict}`
      );
    }
  });
}

function severityOf(sev: string): vscode.DiagnosticSeverity {
  switch (sev.toUpperCase()) {
    case "FATAL":
    case "SILENT":
      return vscode.DiagnosticSeverity.Error;
    case "WARN":
      return vscode.DiagnosticSeverity.Warning;
    default:
      return vscode.DiagnosticSeverity.Information;
  }
}

// Best-effort: find a line that mentions a quoted token from the message
// (e.g. a refdes 'R1' or node '2'), so the diagnostic lands near the culprit.
// Falls back to line 0 when nothing matches.
function locate(doc: vscode.TextDocument, message: string): vscode.Range {
  const tokens = Array.from(message.matchAll(/'([^']+)'/g)).map((m) => m[1]);
  for (const tok of tokens) {
    if (!tok || tok.length > 40) {
      continue;
    }
    for (let i = 0; i < doc.lineCount; i++) {
      const text = doc.lineAt(i).text;
      const re = new RegExp(`(^|\\s|:)${escapeRegExp(tok)}(\\s|$|:)`, "i");
      if (re.test(text)) {
        return doc.lineAt(i).range;
      }
    }
  }
  return doc.lineAt(0).range;
}

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function applyDiagnostics(doc: vscode.TextDocument, results: SgResult[]) {
  const diags: vscode.Diagnostic[] = [];
  for (const r of results) {
    for (const issue of r.issues) {
      // INFO-level "converted" notices etc. are not worth surfacing inline.
      if (issue.code === "converted") {
        continue;
      }
      const d = new vscode.Diagnostic(
        locate(doc, issue.message),
        `${issue.message}`,
        severityOf(issue.severity)
      );
      d.source = "spiceguard";
      d.code = issue.code;
      diags.push(d);
    }
  }
  diagnostics.set(doc.uri, diags);
}

function handleNoOutput(
  err: ExecFileException | null,
  stderr: string,
  bin: string,
  manual: boolean
) {
  const enoent = !!err && err.code === "ENOENT";
  if (enoent) {
    if (!warnedMissing || manual) {
      warnedMissing = true;
      vscode.window.showWarningMessage(
        `spiceguard not found ('${bin}'). Install it with: pip install spiceguard ` +
          `(or set 'spiceguard.path').`
      );
    }
    return;
  }
  // exit 3 = ngspice missing; surface its stderr message.
  const msg = (stderr || "").trim();
  if (msg) {
    output.appendLine(msg);
    if (manual) {
      vscode.window.showWarningMessage("spiceguard: " + msg.split("\n")[0]);
    }
  }
}
