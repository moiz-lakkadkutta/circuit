const btn = document.getElementById("check");
const result = document.getElementById("result");
const netlist = document.getElementById("netlist");

// Per-channel attribution: links are shared as ?src=hn, ?src=kicad-forum, ...
const src = new URLSearchParams(location.search).get("src");
if (src) document.getElementById("src-field").value = src;

async function boot() {
  const { loadPyodide } = await import(
    "https://cdn.jsdelivr.net/pyodide/v0.26.1/full/pyodide.mjs");
  const pyodide = await loadPyodide();
  await pyodide.loadPackage("micropip");
  const micropip = pyodide.pyimport("micropip");
  // The wheel is built and copied into site/wheels/ by the Pages workflow.
  const wheelName = document.querySelector('meta[name="spiceguard-wheel"]')
    ?.content ?? "wheels/spiceguard-0.3.0-py3-none-any.whl";
  await micropip.install(wheelName);

  btn.disabled = false;
  btn.textContent = "Check my netlist";
  btn.addEventListener("click", () => {
    pyodide.globals.set("netlist_text", netlist.value);
    const raw = pyodide.runPython(`
import json
from spiceguard.static_eval import evaluate_static
json.dumps(evaluate_static(netlist_text))
`);
    const r = JSON.parse(raw);
    result.hidden = false;
    const lines = [`verdict: ${r.verdict}  (${r.mode})`];
    for (const i of r.issues) {
      lines.push(`\n[${i.severity}] ${i.code}\n→ ${i.message}`);
    }
    if (r.issues.length === 0) lines.push("\nNo static trust issues found.");
    result.textContent = lines.join("\n");
  });
}

boot().catch((e) => {
  btn.textContent = "Demo failed to load — see console";
  console.error(e);
});
