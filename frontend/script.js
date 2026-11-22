/* =====================================================================
   C Compiler Error Explainer — frontend application logic
   Talks to the Flask backend (backend/app.py) over a small JSON API and
   renders every compiler phase into its own tab. No AI, no external
   API calls happen anywhere in this file or the backend it talks to.
   ===================================================================== */

// If you changed PORT when starting app.py, update this to match.
const API_BASE = "";

let editor = null;
let currentResult = null;   // last successful /analyze response
let selectedErrorIndex = 0; // which error is shown in the Error Explanation tab

const PHASE_TO_TAB = {
  lexical_analysis: "tokens",
  syntax_analysis: "parsetree",
  semantic_analysis: "symboltable",
  intermediate_code: "intermediate",
  optimization: "optimization",
  code_generation: "targetcode",
};

const PHASE_LABELS = {
  lexical_analysis: "Lexer",
  syntax_analysis: "Parser",
  semantic_analysis: "Semantic",
  intermediate_code: "IR",
  optimization: "Optimize",
  code_generation: "CodeGen",
};

const DEFAULT_CODE = `#include <stdio.h>

int main() {
    int x = 10;
    int y = 20;
    int sum = x + y;
    printf("%d", sum);
    return 0;
}
`;

// ---------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  editor = CodeMirror.fromTextArea(document.getElementById("code-editor"), {
    mode: "text/x-csrc",
    theme: "dracula",
    lineNumbers: true,
    indentUnit: 4,
    tabSize: 4,
    matchBrackets: true,
    autofocus: true,
  });
  editor.setValue(DEFAULT_CODE);

  renderPipelineSkeleton();
  checkBackendHealth();
  loadExamples();

  document.getElementById("analyze-btn").addEventListener("click", runAnalyze);
  document.getElementById("clear-btn").addEventListener("click", () => editor.setValue(""));
  document.getElementById("copy-btn").addEventListener("click", copyCode);
  document.getElementById("example-select").addEventListener("change", onExampleSelected);

  document.getElementById("tabs").addEventListener("click", (e) => {
    const btn = e.target.closest(".tab-btn");
    if (btn) switchTab(btn.dataset.tab);
  });
});

// ---------------------------------------------------------------------
// Backend health + examples
// ---------------------------------------------------------------------
async function checkBackendHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    await res.json(); // just confirms the backend responded with valid JSON
    setStatusPill("backend-dot", "backend-status-text", true, "Backend Ready");
  } catch (err) {
    setStatusPill("backend-dot", "backend-status-text", false, "Backend Unreachable");
    showToast("Cannot reach the backend at " + API_BASE + ". Is 'python app.py' running?", true);
  }
}

function setStatusPill(dotId, textId, ok, text, forceClass) {
  const dot = document.getElementById(dotId);
  const label = document.getElementById(textId);
  dot.className = "status-dot " + (forceClass || (ok ? "on" : "off"));
  label.textContent = text;
}

async function loadExamples() {
  try {
    const res = await fetch(`${API_BASE}/examples`);
    const data = await res.json();
    const select = document.getElementById("example-select");
    data.examples.forEach((ex) => {
      const opt = document.createElement("option");
      opt.value = ex.id;
      opt.textContent = ex.title;
      opt.dataset.code = ex.code;
      opt.title = ex.description;
      select.appendChild(opt);
    });
    window.__examples = data.examples;
  } catch (err) {
    // Non-fatal: example dropdown just stays empty if the backend is down.
  }
}

function onExampleSelected(e) {
  const id = e.target.value;
  if (!id || !window.__examples) return;
  const ex = window.__examples.find((x) => x.id === id);
  if (ex) editor.setValue(ex.code);
}

function copyCode() {
  navigator.clipboard.writeText(editor.getValue()).then(() => showToast("Code copied to clipboard."));
}

// ---------------------------------------------------------------------
// Run analysis
// ---------------------------------------------------------------------
async function runAnalyze() {
  const code = editor.getValue();
  if (!code.trim()) {
    showToast("Please write or load some C code first.", true);
    return;
  }

  const btn = document.getElementById("analyze-btn");
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Analyzing…';

  try {
    const res = await fetch(`${API_BASE}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        code,
        use_gcc: document.getElementById("gcc-checkbox").checked,
      }),
    });
    const data = await res.json();

    if (!res.ok || !data.success) {
      showToast(data.message || "Analysis failed.", true);
      return;
    }

    currentResult = data;
    selectedErrorIndex = 0;
    renderAll(data);

    if (data.errors && data.errors.length > 0) {
      switchTab("errors");
    } else {
      switchTab("overview");
    }
  } catch (err) {
    showToast("Could not reach the backend. Is 'python app.py' running on " + API_BASE + "?", true);
  } finally {
    btn.disabled = false;
    btn.innerHTML = "▶ Analyze Code";
  }
}

// ---------------------------------------------------------------------
// Tabs
// ---------------------------------------------------------------------
function switchTab(tabId) {
  document.querySelectorAll(".tab-btn").forEach((b) => b.classList.toggle("active", b.dataset.tab === tabId));
  document.querySelectorAll(".tab-pane").forEach((p) => p.classList.toggle("active", p.id === "tab-" + tabId));
}

// ---------------------------------------------------------------------
// Render everything
// ---------------------------------------------------------------------
function renderAll(data) {
  renderPipeline(data.pipeline_status, data.skipped_reason);
  renderOverview(data);
  renderTokens(data.tokens);
  renderParseTree(data.parse_tree);
  renderSymbolTable(data.symbol_table);
  renderIntermediate(data.intermediate_code, data.skipped_reason);
  renderOptimization(data.optimization, data.skipped_reason);
  renderTargetCode(data.target_code, data.skipped_reason);
  renderErrors(data.errors, data.warnings);
  renderExplanation();
  renderGcc(data.gcc);
}

// ----- Pipeline strip -----
const PIPELINE_ORDER = [
  ["lexical_analysis", "Lexer", "1"],
  ["syntax_analysis", "Parser", "2"],
  ["semantic_analysis", "Semantic", "3"],
  ["intermediate_code", "IR", "4"],
  ["optimization", "Optimize", "5"],
  ["code_generation", "CodeGen", "6"],
];

const STATUS_ICON = { success: "✓", error: "✗", not_processed: "○" };

function renderPipelineSkeleton() {
  renderPipeline({}, null);
}

function renderPipeline(status, skippedReason) {
  const container = document.getElementById("pipeline-nodes");
  container.innerHTML = "";

  PIPELINE_ORDER.forEach(([key, label, num], i) => {
    const st = status[key] || "not_processed";
    const node = document.createElement("div");
    node.className = "pipeline-node " + st;
    node.innerHTML = `
      <div class="node-circle">${STATUS_ICON[st] || num}</div>
      <div class="node-label">${label}</div>`;
    node.addEventListener("click", () => switchTab(PHASE_TO_TAB[key]));
    container.appendChild(node);

    if (i < PIPELINE_ORDER.length - 1) {
      const connector = document.createElement("div");
      connector.className = "pipeline-connector";
      container.appendChild(connector);
    }
  });

  const note = document.getElementById("pipeline-note");
  if (skippedReason) {
    note.textContent = "ⓘ " + skippedReason;
    note.classList.add("visible");
  } else {
    note.classList.remove("visible");
  }
}

// ----- Overview -----
function renderOverview(data) {
  const o = data.overview;
  const ok = o.errors === 0;
  document.getElementById("tab-overview").innerHTML = `
    <div class="status-banner ${ok ? "ok" : "fail"}">
      <strong>${ok ? "✓ Compilation Analysis Successful" : "✗ Compilation Failed"}</strong>
      &nbsp;— ${ok ? "No errors detected." : o.errors + " error(s) found. See the Errors tab for details."}
    </div>
    <div class="overview-grid" style="margin-top:16px;">
      <div class="stat-card"><div class="stat-value">${o.lines}</div><div class="stat-label">Lines</div></div>
      <div class="stat-card"><div class="stat-value">${o.tokens}</div><div class="stat-label">Tokens</div></div>
      <div class="stat-card"><div class="stat-value">${o.symbols}</div><div class="stat-label">Symbols</div></div>
      <div class="stat-card error"><div class="stat-value">${o.errors}</div><div class="stat-label">Errors</div></div>
      <div class="stat-card warning"><div class="stat-value">${o.warnings}</div><div class="stat-label">Warnings</div></div>
    </div>
    ${data.skipped_reason ? `<div class="skip-note">ⓘ ${escapeHtml(data.skipped_reason)}</div>` : ""}
    ${data.gcc ? renderGccSummaryInline(data.gcc) : ""}
  `;
}

function renderGccSummaryInline(gcc) {
  if (!gcc.available) return `<div class="skip-note">GCC comparison requested, but GCC is not installed on this system.</div>`;
  return `<div class="skip-note">Real GCC compilation ${gcc.success ? "succeeded" : "failed"} — see the Errors tab / console for details.</div>`;
}

function renderGcc(gcc) {
  // Currently surfaced inline in the Overview tab (see renderGccSummaryInline).
  // Kept as a separate function so a dedicated GCC panel can be added later
  // without touching renderAll()'s call sites.
}

// ----- Tokens -----
const CATEGORY_CLASS = {
  KEYWORD: "kw",
  IDENTIFIER: "id",
  INT_CONSTANT: "num",
  FLOAT_CONSTANT: "num",
  STRING_LITERAL: "str",
  CHAR_LITERAL: "str",
  OPERATOR: "op",
  DELIMITER: "delim",
  PREPROCESSOR: "pre",
  INVALID_CHARACTER: "err",
};

function renderTokens(tokens) {
  if (!tokens || tokens.length === 0) {
    document.getElementById("tab-tokens").innerHTML = emptyState("No tokens yet — analyze some code first.");
    return;
  }
  const rows = tokens.map((t) => `
    <tr>
      <td>${t.line}</td>
      <td>${escapeHtml(t.lexeme)}</td>
      <td>${t.token}</td>
      <td><span class="badge ${CATEGORY_CLASS[t.token] || "op"}">${t.category}</span></td>
    </tr>`).join("");

  document.getElementById("tab-tokens").innerHTML = `
    <table class="data-table">
      <thead><tr><th>Line</th><th>Lexeme</th><th>Token</th><th>Category</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

// ----- Parse tree -----
function renderParseTree(tree) {
  if (!tree || !tree.children) {
    document.getElementById("tab-parsetree").innerHTML = emptyState("No parse tree yet — analyze some code first.");
    return;
  }
  document.getElementById("tab-parsetree").innerHTML = `<div class="tree">${treeNodeToHtml(tree)}</div>`;
}

function treeNodeToHtml(node) {
  if (!node) return "";
  const label = node.label && node.label !== node.type ? `<span class="node-label"> ${escapeHtml(node.label)}</span>` : "";
  const children = (node.children || []).map((c) => `<li>${treeNodeToHtml(c)}</li>`).join("");
  return `
    <span class="node-chip"><span class="node-type">${node.type}</span>${label}</span>
    ${children ? `<ul>${children}</ul>` : ""}`;
}

// ----- Symbol table -----
function renderSymbolTable(symbols) {
  if (!symbols || symbols.length === 0) {
    document.getElementById("tab-symboltable").innerHTML = emptyState("No symbols recorded yet — analyze some code first.");
    return;
  }
  const rows = symbols.map((s) => `
    <tr>
      <td>${escapeHtml(s.name)}</td>
      <td>${escapeHtml(s.type)}</td>
      <td>${escapeHtml(s.scope)}</td>
      <td>${s.line}</td>
      <td>${s.kind}</td>
    </tr>`).join("");

  document.getElementById("tab-symboltable").innerHTML = `
    <table class="data-table">
      <thead><tr><th>Name</th><th>Type</th><th>Scope</th><th>Line</th><th>Kind</th></tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

// ----- Intermediate code (TAC) -----
function renderIntermediate(instructions, skippedReason) {
  if (!instructions || instructions.length === 0) {
    document.getElementById("tab-intermediate").innerHTML = skippedReason
      ? emptyState(skippedReason)
      : emptyState("No intermediate code yet — analyze some code first.");
    return;
  }
  document.getElementById("tab-intermediate").innerHTML = `
    <p style="color:var(--text-secondary); font-size:12.5px; margin-bottom:12px;">Three Address Code (TAC) — before optimization</p>
    ${codeBlockHtml(instructions, (i) => i.code)}`;
}

function codeBlockHtml(instructions, codeGetter) {
  const lines = instructions.map((instr) => {
    const kindClass = instr.kind === "note" ? "note-line" : instr.kind === "call" ? "call-line" : "";
    return `<div class="code-line ${kindClass}">
      <span class="line-no">${instr.line != null ? instr.line : ""}</span>
      <span class="line-text">${escapeHtml(codeGetter(instr))}</span>
    </div>`;
  }).join("");
  return `<div class="code-block">${lines}</div>`;
}

// ----- Optimization -----
function renderOptimization(opt, skippedReason) {
  if (!opt || !opt.before || opt.before.length === 0) {
    document.getElementById("tab-optimization").innerHTML = skippedReason
      ? emptyState(skippedReason)
      : emptyState("No optimization data yet — analyze some code first.");
    return;
  }

  const compareHtml = `
    <div class="opt-compare">
      <div>
        <div class="compare-label">Before Optimization</div>
        ${codeBlockHtml(opt.before, (i) => i.code)}
      </div>
      <div>
        <div class="compare-label">After Optimization</div>
        ${codeBlockHtml(opt.after, (i) => i.code)}
      </div>
    </div>`;

  let logHtml;
  if (opt.applied.length === 0) {
    logHtml = `<div class="empty-state" style="padding:24px;">No further optimizations were applicable to this code.</div>`;
  } else {
    logHtml = opt.applied.map((a) => `
      <div class="opt-log-item">
        <span class="opt-tag">${escapeHtml(a.technique)}</span>
        <span class="opt-before">${escapeHtml(a.before)}</span>
        <span>→</span>
        <span class="opt-after">${escapeHtml(a.after)}</span>
        ${a.line != null ? `<span style="color:var(--text-muted); font-family:var(--font-mono); font-size:11px;">(line ${a.line})</span>` : ""}
      </div>`).join("");
  }

  document.getElementById("tab-optimization").innerHTML = `
    ${compareHtml}
    <div class="compare-label" style="margin-bottom:8px;">Optimizations Applied</div>
    ${logHtml}
    <p style="color:var(--text-muted); font-size:11.5px; margin-top:14px; font-family:var(--font-mono);">
      ⓘ These are educational optimizations (constant folding, constant propagation, algebraic
      simplification, dead code elimination on temporaries) — not a full industrial optimizer.
    </p>`;
}

// ----- Target code -----
function renderTargetCode(target, skippedReason) {
  if (!target || target.length === 0) {
    document.getElementById("tab-targetcode").innerHTML = skippedReason
      ? emptyState(skippedReason)
      : emptyState("No target code yet — analyze some code first.");
    return;
  }
  document.getElementById("tab-targetcode").innerHTML = `
    <p style="color:var(--text-secondary); font-size:12.5px; margin-bottom:12px;">
      Generated Target Code (educational pseudo-assembly — not real x86/ARM machine code)</p>
    ${codeBlockHtml(target, (i) => i.instruction)}`;
}

// ----- Errors -----
function renderErrors(errors, warnings) {
  const badge = document.getElementById("error-count-badge");
  if (errors && errors.length > 0) {
    badge.style.display = "inline-block";
    badge.textContent = errors.length;
  } else {
    badge.style.display = "none";
  }

  if ((!errors || errors.length === 0) && (!warnings || warnings.length === 0)) {
    document.getElementById("tab-errors").innerHTML = `
      <div class="status-banner ok"><strong>✓ No errors or warnings found.</strong></div>`;
    return;
  }

  let html = "";
  if (errors && errors.length > 0) {
    html += `<h3 style="font-family:var(--font-display); font-size:14px; margin:0 0 12px;">${errors.length} Error${errors.length > 1 ? "s" : ""} Found</h3>`;
    html += errors.map((e, idx) => errorCardHtml(e, idx, false)).join("");
  }
  if (warnings && warnings.length > 0) {
    html += `<h3 style="font-family:var(--font-display); font-size:14px; margin:22px 0 12px;">${warnings.length} Warning${warnings.length > 1 ? "s" : ""}</h3>`;
    html += warnings.map((w) => errorCardHtml(w, null, true)).join("");
  }

  document.getElementById("tab-errors").innerHTML = html;

  document.querySelectorAll(".error-card[data-error-index]").forEach((card) => {
    card.addEventListener("click", () => {
      selectedErrorIndex = parseInt(card.dataset.errorIndex, 10);
      renderExplanation();
      switchTab("aiexplain");
    });
  });
}

function errorCardHtml(e, index, isWarning) {
  const clickAttr = index !== null ? `data-error-index="${index}"` : "";
  return `
    <div class="error-card ${isWarning ? "warning-card" : ""}" ${clickAttr}>
      <div class="error-head">
        <span class="error-type">${isWarning ? "⚠ Warning" : "✗ " + e.error_type}</span>
        <span class="error-line">${e.phase || ""}${e.line != null ? " · Line " + e.line : ""}</span>
      </div>
      <div class="error-message">${escapeHtml(e.message)}</div>
      ${e.source_line ? `<div class="error-source">${escapeHtml(e.source_line)}</div>` : ""}
      ${!isWarning ? `<div class="error-hint">Click for the rule-based explanation →</div>` : ""}
    </div>`;
}

// ----- Error Explanation (100% rule-based, no AI) -----
function renderExplanation() {
  const container = document.getElementById("tab-aiexplain");
  if (!currentResult || !currentResult.errors || currentResult.errors.length === 0) {
    container.innerHTML = emptyState("No errors to explain. Analyze code that contains an error to see its rule-based explanation here.");
    return;
  }

  const errors = currentResult.errors;
  if (selectedErrorIndex >= errors.length) selectedErrorIndex = 0;
  const err = errors[selectedErrorIndex];
  const exp = err.explanation;

  const picker = errors.map((e, i) => `
    <button class="${i === selectedErrorIndex ? "active" : ""}" data-idx="${i}">
      Error ${i + 1}: ${e.phase}
    </button>`).join("");

  container.innerHTML = `
    <div class="error-picker">${picker}</div>
    <div class="ai-header">
      <span class="ai-badge">📘 Error Explanation</span>
    </div>
    <div class="ai-status-line">Rule ${escapeHtml(exp.error_code || "")} · Generated from compiler analysis (no AI, fully offline)</div>

    <div class="ai-section">
      <h4>What happened?</h4>
      <p>${escapeHtml(exp.explanation)}</p>
    </div>
    <div class="ai-section">
      <h4>Why is it a problem?</h4>
      <p>${escapeHtml(exp.reason)}</p>
    </div>
    <div class="ai-section">
      <h4>How to fix it</h4>
      <p>${escapeHtml(exp.solution)}</p>
    </div>
    <div class="ai-section">
      <h4>Suggested correction / example</h4>
      <div class="corrected-code">${escapeHtml(exp.corrected_code)}</div>
    </div>
    <div class="ai-section">
      <h4>Beginner tip</h4>
      <div class="tip-box">${escapeHtml(exp.tip)}</div>
    </div>
  `;

  container.querySelectorAll(".error-picker button").forEach((b) => {
    b.addEventListener("click", () => {
      selectedErrorIndex = parseInt(b.dataset.idx, 10);
      renderExplanation();
    });
  });
}

// ---------------------------------------------------------------------
// Small utilities
// ---------------------------------------------------------------------
function emptyState(text) {
  return `<div class="empty-state">${escapeHtml(text)}</div>`;
}

function escapeHtml(text) {
  if (text === null || text === undefined) return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

let toastTimer = null;
function showToast(message, isError) {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.className = "toast visible" + (isError ? " error" : "");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("visible"), 4500);
}
