// BrewFlow AI Operations Console — front-end controller (refactored v2)
// Same backend integration as before; new sidebar/drawer/subtabs layout.

(function () {
  "use strict";

  // ===================================================================
  // State
  // ===================================================================
  window.__lastRun = null;
  // Map of "<workflow_type>#<item_id>" → "approved" | "escalated" | "rejected" | "edited"
  // Used by Review Queue filter chips.
  window.__reviewState = {};

  // ===================================================================
  // Tiny DOM helpers
  // ===================================================================
  function el(tag, attrs, children) {
    const e = document.createElement(tag);
    if (attrs) {
      Object.entries(attrs).forEach(([k, v]) => {
        if (v == null || v === false) return;
        if (k === "class") e.className = v;
        else if (k === "html") e.innerHTML = v;
        else if (k === "onclick") e.addEventListener("click", v);
        else if (k === "hidden" && v === true) e.setAttribute("hidden", "");
        else e.setAttribute(k, v);
      });
    }
    (children || []).forEach((c) => {
      if (c == null) return;
      e.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    });
    return e;
  }

  async function postJSON(url, body) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
    const data = await res.json().catch(() => ({ error: "Invalid JSON response" }));
    return { ok: res.ok, status: res.status, data };
  }

  // ===================================================================
  // Form validation — per-field inline messages
  // ===================================================================
  // Each required field has a <span class="field-error" id="<id>-err"> right
  // below its input. validateFields() flips that span on/off with a
  // specific, human-readable message.  No summary block is rendered.

  const FIELD_ERROR_MSG = {
    "full-store":   "Please select a store.",
    "full-date":    "Please select a date.",
    "full-hour":    "Please select an hour.",
    "full-request": "Please enter a customer request.",

    "mgr-store":    "Please select a store.",
    "mgr-date":     "Please select a date.",
    "mgr-hour":     "Please select an hour.",

    "bar-store":    "Please select a store.",
    "bar-date":     "Please select a date.",
    "bar-hour":     "Please select an hour.",
    "bar-request":  "Please enter a customer request.",

    "ord-store":    "Please select a store.",
    "ord-date":     "Please select a date.",
    "ord-raw":      "Please enter a raw order.",
  };

  function setFieldError(id, message) {
    const node = document.getElementById(id);
    if (node) {
      node.classList.add("invalid");
      node.setAttribute("aria-invalid", "true");
    }
    const errEl = document.getElementById(`${id}-err`);
    if (errEl) {
      errEl.textContent = message;
      errEl.hidden = false;
    }
  }

  function clearFieldError(id) {
    const node = document.getElementById(id);
    if (node) {
      node.classList.remove("invalid");
      node.removeAttribute("aria-invalid");
    }
    const errEl = document.getElementById(`${id}-err`);
    if (errEl) errEl.hidden = true;
  }

  function validateFields(ids) {
    let valid = true;
    let firstInvalid = null;
    ids.forEach((id) => {
      const node = document.getElementById(id);
      if (!node) return;
      const val = (node.value || "").trim();
      if (!val) {
        setFieldError(id, FIELD_ERROR_MSG[id] || "This field is required.");
        if (!firstInvalid) firstInvalid = node;
        valid = false;
      } else {
        clearFieldError(id);
      }
    });
    if (!valid && firstInvalid && typeof firstInvalid.scrollIntoView === "function") {
      firstInvalid.scrollIntoView({ behavior: "smooth", block: "center" });
      // Don't steal focus from buttons too aggressively; only focus on submit failure.
      try { firstInvalid.focus({ preventScroll: true }); } catch (e) { /* noop */ }
    }
    return valid;
  }

  // Live-clear inline errors as the user provides input
  Object.keys(FIELD_ERROR_MSG).forEach((id) => {
    const node = document.getElementById(id);
    if (!node) return;
    const handler = () => {
      const val = (node.value || "").trim();
      if (val) clearFieldError(id);
    };
    node.addEventListener("change", handler);
    node.addEventListener("input", handler);
  });

  function readPrefs(idPrefix) {
    const prefs = {};
    const map = {
      temp: "temperature", sweet: "sweetness", milk: "milk_preference",
      caffeine: "caffeine", coffee: "coffee_preference", lowcal: "low_calorie",
      food: "food_only",
    };
    Object.keys(map).forEach((k) => {
      const inp = document.getElementById(`${idPrefix}-pref-${k}`);
      if (!inp || !inp.value.trim()) return;
      let v = inp.value.trim();
      if (k === "lowcal" || k === "food") v = /^(true|1|yes)$/i.test(v);
      prefs[map[k]] = v;
    });
    return Object.keys(prefs).length ? prefs : null;
  }

  // ===================================================================
  // Sidebar navigation
  // ===================================================================
  function switchTab(tab) {
    document.querySelectorAll(".nav-item").forEach((n) => {
      n.classList.toggle("active", n.dataset.tab === tab);
    });
    document.querySelectorAll(".view").forEach((v) => {
      v.classList.toggle("active", v.id === `view-${tab}`);
    });
    // On mobile, close the sidebar after picking
    document.getElementById("sidebar").classList.remove("open");
  }
  // Expose so inline scripts can call switchTab without IIFE scoping issues
  window.switchTab = switchTab;
  document.querySelectorAll(".nav-item").forEach((n) => {
    n.addEventListener("click", () => switchTab(n.dataset.tab));
  });
  document.getElementById("sidebar-toggle").addEventListener("click", () => {
    document.getElementById("sidebar").classList.toggle("open");
  });
  // CTA buttons inside empty states ("Go to Full Workflow")
  document.body.addEventListener("click", (e) => {
    const j = e.target.closest && e.target.closest("[data-jump]");
    if (j) switchTab(j.dataset.jump);
  });

  // ===================================================================
  // Audit drawer
  // ===================================================================
  const drawer = document.getElementById("audit-drawer");
  const handle = document.getElementById("audit-handle");
  function toggleDrawer(force) {
    const open = force != null ? force : drawer.getAttribute("aria-expanded") !== "true";
    drawer.setAttribute("aria-expanded", open ? "true" : "false");
  }
  handle.addEventListener("click", () => toggleDrawer());

  // ===================================================================
  // Evidence Center sub-tabs
  // ===================================================================
  document.querySelectorAll(".subtab").forEach((s) => {
    s.addEventListener("click", () => {
      document.querySelectorAll(".subtab").forEach((x) => x.classList.remove("active"));
      document.querySelectorAll(".subpanel").forEach((x) => x.classList.remove("active"));
      s.classList.add("active");
      const panel = document.getElementById(`sub-${s.dataset.sub}`);
      if (panel) panel.classList.add("active");
    });
  });

  // ===================================================================
  // Status helpers
  // ===================================================================
  function statusBanner(status) {
    const t = status === "success" ? "ok"
            : status === "warning" ? "warn"
            : status === "needs_review" ? "review"
            : status === "error" ? "err"
            : "ok";
    return el("div", { class: `status-banner ${t}` }, [
      el("strong", null, [`Status: ${status || "unknown"}`]),
    ]);
  }

  function fvBadgeClass(status) {
    return status === "plausible" ? "success"
         : status === "needs_review" ? "warning"
         : status === "weak" ? "error"
         : "gray";
  }

  // ===================================================================
  // Face Validity card
  // ===================================================================
  // ── Compact summary strip — 4 key fields in one line ───────────────────────
  function faceValiditySummary(fv) {
    if (!fv) return null;
    const cls = fv.status || "not_applicable";
    const pill = fvBadgeClass(cls);
    const strip = el("div", { class: `fv-summary fv-summary-${cls}` });
    strip.appendChild(el("span", { class: "fvs-label" }, ["🎯 Face Validity"]));
    strip.appendChild(el("span", { class: `pill ${pill} fvs-status` }, [fv.status || "—"]));
    strip.appendChild(el("span", { class: "fvs-sep" }, ["·"]));
    strip.appendChild(el("span", { class: "fvs-item" }, [
      el("span", { class: "fvs-key" }, ["Confidence "]),
      el("span", { class: "fvs-val" }, [fv.confidence || "—"]),
    ]));
    strip.appendChild(el("span", { class: "fvs-sep" }, ["·"]));
    strip.appendChild(el("span", { class: "fvs-item" }, [
      el("span", { class: "fvs-key" }, ["Quality "]),
      el("span", { class: "fvs-val" }, [
        `${(fv.evidence_quality?.score ?? 0).toFixed(2)} ${fv.evidence_quality?.label || "—"}`,
      ]),
    ]));
    strip.appendChild(el("span", { class: "fvs-sep" }, ["·"]));
    strip.appendChild(el("span", { class: "fvs-item" }, [
      el("span", { class: "fvs-key" }, ["Action "]),
      el("span", { class: "fvs-val" }, [fv.recommended_action || "—"]),
    ]));
    return strip;
  }

  // ── Full detail card body (used inside collapsible and Evidence Center) ──────
  function faceValidityDetailBody(fv) {
    const cls = fv.status || "not_applicable";
    const body = el("div", { class: `fv-detail-body` });
    body.appendChild(el("div", { class: "fv-row" }, [
      el("span", null, [el("strong", null, ["Status: "]),
        el("span", { class: `pill ${fvBadgeClass(cls)}` }, [fv.status || "—"]),
      ]),
      el("span", null, [el("strong", null, ["Confidence: "]), fv.confidence || "—"]),
      el("span", null, [
        el("strong", null, ["Evidence quality: "]),
        `${(fv.evidence_quality?.score ?? 0).toFixed(2)} (${fv.evidence_quality?.label || "—"})`,
      ]),
      el("span", null, [el("strong", null, ["Recommended action: "]), fv.recommended_action || "—"]),
      el("span", null, [el("strong", null, ["Human review required: "]), fv.human_review_required ? "yes" : "no"]),
    ]));
    if (fv.anchors_used?.length) {
      const row = el("div", { class: "fv-row" }, [el("strong", null, ["Anchors: "])]);
      fv.anchors_used.forEach((a) => row.appendChild(el("span", { class: "chip" }, [a])));
      body.appendChild(row);
    }
    if (fv.supporting_reasons?.length) {
      body.appendChild(el("h4", null, ["Supporting reasons"]));
      const ul = el("ul", { class: "fv-list" });
      fv.supporting_reasons.forEach((r) => ul.appendChild(el("li", null, [r])));
      body.appendChild(ul);
    }
    if (fv.concerns?.length) {
      body.appendChild(el("h4", null, ["Concerns"]));
      const ul = el("ul", { class: "fv-list" });
      fv.concerns.forEach((r) => ul.appendChild(el("li", null, [r])));
      body.appendChild(ul);
    }
    return body;
  }

  // ── Collapsible details panel — collapsed by default ────────────────────────
  function faceValidityCollapsible(fv) {
    if (!fv) return null;
    const cls = fv.status || "not_applicable";
    const pill = fvBadgeClass(cls);
    const details = el("details", { class: `fv-collapsible fv-collapsible-${cls}` });
    const summary = el("summary", null, [
      el("span", { class: "fvc-label" }, ["🎯 Face Validity Details"]),
      el("span", { class: `pill ${pill}` }, [fv.status || "—"]),
    ]);
    details.appendChild(summary);
    details.appendChild(el("div", { class: "fv-collapsible-body" }, [faceValidityDetailBody(fv)]));
    return details;
  }

  // ── Legacy full card — kept for Evidence Center where detail is appropriate ──
  function faceValidityCard(fv) {
    if (!fv) return el("div", { class: "card muted" }, ["No face_validity attached."]);
    const cls = fv.status || "not_applicable";
    const card = el("div", { class: `fv-card ${cls}` });
    card.appendChild(el("h3", null, [
      "🎯 Face Validity ",
      el("span", { class: `pill ${fvBadgeClass(cls)}` }, [fv.status || "—"]),
    ]));
    card.appendChild(faceValidityDetailBody(fv));
    return card;
  }

  // ===================================================================
  // Review action buttons
  // ===================================================================
  function reviewActionButtons(targetKey, workflowType) {
    const wrap = el("div", { class: "review-actions" });
    const make = (cls, label, action) => {
      const b = el("button", { class: cls }, [label]);
      b.addEventListener("click", () => handleReviewAction(action, targetKey, workflowType));
      return b;
    };
    wrap.appendChild(make("approve", "Approve", "approve"));
    wrap.appendChild(make("edit", "Edit", "edit"));
    wrap.appendChild(make("reject", "Reject + Rerun", "reject_rerun"));
    wrap.appendChild(make("escalate", "Escalate", "escalate"));
    return wrap;
  }

  async function handleReviewAction(action, targetKey, workflowType) {
    if (action === "edit" || action === "escalate") {
      openModal(action === "edit" ? "Edit / annotate" : "Escalation note", async (notes) => {
        await postReviewAction(action, targetKey, workflowType, notes);
      });
    } else {
      await postReviewAction(action, targetKey, workflowType, "");
    }
  }

  async function postReviewAction(action, targetKey, workflowType, notes) {
    const { ok, data } = await postJSON("/api/review_action", {
      action, target: targetKey, workflow_type: workflowType, notes,
    });
    if (ok) {
      flashBanner(`Recorded: ${action}${notes ? " — " + notes : ""}`, "ok");
      // Track for the Review Queue filter
      const mapAction = { approve: "approved", reject_rerun: "rejected", escalate: "escalated", edit: "edited" };
      window.__reviewState[targetKey] = mapAction[action] || "acted";
      // Re-render the review queue (preserving filter)
      if (window.__lastRun) renderReviewQueue(window.__lastRun);
      await refreshAudit({ open: true });
    } else {
      flashBanner(`Review action failed: ${data.error || "unknown"}`, "err");
    }
  }

  // ===================================================================
  // Modal (Edit / Escalate)
  // ===================================================================
  const modal = document.getElementById("modal-backdrop");
  const modalNotes = document.getElementById("modal-notes");
  const modalTitle = document.getElementById("modal-title");
  let modalCallback = null;
  function openModal(title, onSubmit) {
    modalTitle.textContent = title;
    modalNotes.value = "";
    modal.classList.remove("hidden");
    modalCallback = onSubmit;
    modalNotes.focus();
  }
  function closeModal() { modal.classList.add("hidden"); modalCallback = null; }
  document.getElementById("modal-cancel").addEventListener("click", closeModal);
  document.getElementById("modal-submit").addEventListener("click", async () => {
    const notes = modalNotes.value.trim();
    const cb = modalCallback;
    closeModal();
    if (cb) await cb(notes);
  });

  // ===================================================================
  // Evidence Center render — split across 5 sub-panels
  // ===================================================================
  function renderEvidenceCenter(run) {
    const empty = document.getElementById("evidence-empty");
    const populated = document.getElementById("evidence-populated");
    if (!run) {
      empty.hidden = false;
      populated.hidden = true;
      return;
    }
    empty.hidden = true;
    populated.hidden = false;

    const ep = run.evidence_package || {};

    // ── Tool / Data ──
    const tool = document.getElementById("sub-tool");
    tool.innerHTML = "";
    const tools = ep.tool_outputs || [];
    if (!tools.length) tool.appendChild(emptyInline("No tool outputs in this run."));
    tools.forEach((t) => {
      tool.appendChild(el("div", { class: "evi-tool" }, [
        el("span", { class: "chip tool" }, ["Tool / MCP"]),
        el("strong", null, [` ${t.tool || "unnamed"} `]),
        el("span", { class: `pill ${t.status === "success" ? "success" : t.status === "warning" ? "warning" : t.status === "needs_review" ? "warning" : "gray"}` }, [t.status || "—"]),
        el("div", { class: "muted small" }, [t.summary || ""]),
      ]));
    });

    // ── RAG ──
    const rag = document.getElementById("sub-rag");
    rag.innerHTML = "";
    const rags = ep.rag_results || ep.rag_snippets || [];
    if (!rags.length) rag.appendChild(emptyInline("No RAG documents were retrieved for this run."));
    rags.forEach((r) => {
      const div = el("div", { class: "evi-rag" }, [
        el("span", { class: "chip rag" }, ["RAG"]),
        el("strong", null, [` ${r.title || r.filename || "(untitled)"} `]),
        r.score != null ? el("span", { class: "pill gray" }, [`score ${Number(r.score).toFixed(2)}`]) : null,
      ]);
      if (r.filename) div.appendChild(el("div", { class: "muted small" }, [`📄 ${r.filename}${r.section_heading ? " — " + r.section_heading : ""}`]));
      if (r.matched_terms?.length) {
        const mt = el("div", null, [el("span", { class: "muted small" }, ["Matched: "])]);
        r.matched_terms.forEach((m) => mt.appendChild(el("span", { class: "chip" }, [m])));
        div.appendChild(mt);
      }
      if (r.snippet) div.appendChild(el("div", { class: "snippet" }, [r.snippet]));
      rag.appendChild(div);
    });

    // ── Assumptions ──
    const asm = document.getElementById("sub-assumptions");
    asm.innerHTML = "";
    const assumptions = ep.assumptions || run.assumptions || [];
    if (!assumptions.length) asm.appendChild(emptyInline("No assumptions recorded for this run."));
    else {
      const ul = el("ul", null);
      assumptions.forEach((a) => ul.appendChild(el("li", null, [a])));
      asm.appendChild(el("div", { class: "card" }, [ul]));
    }

    // ── Warnings ──
    const warn = document.getElementById("sub-warnings");
    warn.innerHTML = "";
    const warnings = run.warnings || ep.warnings || [];
    if (!warnings.length) warn.appendChild(emptyInline("No warnings for this run."));
    else {
      const ul = el("ul", null);
      warnings.forEach((w) => ul.appendChild(el("li", null, [w])));
      warn.appendChild(el("div", { class: "card" }, [ul]));
    }

    // ── Quality + Face Validity ──
    // Evidence Center: show full card (appropriate level of detail here),
    // but still use the collapsible for anchors/reasons/concerns so it's scannable.
    const q = document.getElementById("sub-quality");
    q.innerHTML = "";
    const fvFull = run.face_validity;
    if (fvFull) {
      // Compact summary always visible at top
      const qs = faceValiditySummary(fvFull);
      if (qs) q.appendChild(qs);
      // Full detail card in a collapsible — open by default in Evidence Center
      const qd = el("details", { class: `fv-collapsible fv-collapsible-${fvFull.status || "not_applicable"}` });
      qd.setAttribute("open", "");
      qd.appendChild(el("summary", null, [
        el("span", { class: "fvc-label" }, ["🎯 Face Validity Details"]),
        el("span", { class: `pill ${fvBadgeClass(fvFull.status || "not_applicable")}` }, [fvFull.status || "—"]),
      ]));
      qd.appendChild(el("div", { class: "fv-collapsible-body" }, [faceValidityDetailBody(fvFull)]));
      q.appendChild(qd);
    } else {
      q.appendChild(el("div", { class: "card muted" }, ["No face_validity attached."]));
    }
    const qCard = el("div", { class: "card" }, [
      el("h3", null, ["Evidence Quality"]),
      el("div", null, [
        el("strong", null, ["Score: "]), String(ep.quality_score ?? "—"),
        " · ",
        el("strong", null, ["Label: "]), String(ep.quality_label ?? "—"),
      ]),
      el("div", { class: "muted small" }, [ep.quality_recommendation || ""]),
      el("div", null, [
        el("strong", null, ["Total evidence items: "]), String(ep.evidence_count ?? "—"),
      ]),
    ]);
    q.appendChild(qCard);
  }

  function emptyInline(msg) {
    return el("div", { class: "empty-state" }, [
      el("div", { class: "empty-icon" }, ["—"]),
      el("p", { class: "muted small" }, [msg]),
    ]);
  }

  // ===================================================================
  // Review Queue render
  // ===================================================================
  let __currentReviewFilter = "all";

  function renderReviewQueue(run) {
    const empty = document.getElementById("review-empty");
    const populated = document.getElementById("review-populated");
    if (!run) {
      empty.hidden = false;
      populated.hidden = true;
      return;
    }
    const items = run.review_queue || [];
    if (!items.length) {
      empty.hidden = false;
      populated.hidden = true;
      return;
    }
    empty.hidden = true;
    populated.hidden = false;

    const fvCls = run.face_validity?.status || "not_applicable";
    const list = document.getElementById("review-list");
    list.innerHTML = "";

    items.forEach((q, idx) => {
      const targetKey = `${run.workflow_type}#${q.item || idx}`;
      const state = window.__reviewState[targetKey] || "pending";
      // Filter
      if (__currentReviewFilter !== "all" && state !== __currentReviewFilter) return;

      const div = el("div", { class: `review-item action-${state}` });
      div.appendChild(el("div", { class: "review-head" }, [
        el("span", { class: "chip review" }, ["Human Review"]),
        el("span", { class: "review-title" }, [q.item || "(unnamed)"]),
        el("span", { class: `pill ${fvBadgeClass(fvCls)}` }, [`face_validity: ${fvCls}`]),
        state !== "pending" ? el("span", { class: `pill ${state === "approved" ? "success" : state === "escalated" ? "warning" : state === "rejected" ? "error" : "info"}` }, [state]) : null,
      ]));
      if (q.reason) div.appendChild(el("div", { class: "review-reason" }, [q.reason]));
      if (q.follow_up_question) {
        div.appendChild(el("div", { class: "muted small" }, [el("strong", null, ["Follow-up: "]), q.follow_up_question]));
      }
      if (q.candidates?.length) {
        const ul = el("ul", null);
        q.candidates.forEach((c) => ul.appendChild(el("li", null, [`${c.item || c.canonical_menu_item || JSON.stringify(c).slice(0, 80)}`])));
        div.appendChild(el("details", null, [el("summary", null, ["Candidates"]), ul]));
      }
      div.appendChild(reviewActionButtons(targetKey, run.workflow_type));
      list.appendChild(div);
    });

    if (!list.children.length) {
      list.appendChild(emptyInline(`No items matching filter: ${__currentReviewFilter}.`));
    }
  }

  document.querySelectorAll(".filter").forEach((f) => {
    f.addEventListener("click", () => {
      document.querySelectorAll(".filter").forEach((x) => x.classList.remove("active"));
      f.classList.add("active");
      __currentReviewFilter = f.dataset.filter;
      if (window.__lastRun) renderReviewQueue(window.__lastRun);
    });
  });

  // ===================================================================
  // Workflow output renderer
  // ===================================================================
  function outCard(title, bodyEl, open) {
    const d = el("details", { class: "out-card", open: open ? "" : null });
    d.appendChild(el("summary", null, [title]));
    d.appendChild(el("div", { class: "out-body" }, [bodyEl]));
    return d;
  }

  function runSummaryCard(run) {
    const ep = run.evidence_package || {};
    const fv = run.face_validity || {};
    const fvCls = fv.status || "not_applicable";

    const metrics = el("div", { class: "run-metrics" }, [
      el("div", { class: "run-metric" }, [
        el("div", { class: "label" }, ["Status"]),
        el("div", { class: "value small" }, [
          el("span", { class: `pill ${run.status === "success" ? "success" : run.status === "warning" ? "warning" : run.status === "needs_review" ? "review" : "gray"}` }, [run.status || "—"]),
        ]),
      ]),
      el("div", { class: "run-metric" }, [
        el("div", { class: "label" }, ["Steps"]),
        el("div", { class: "value" }, [String((run.steps || []).length)]),
      ]),
      el("div", { class: "run-metric" }, [
        el("div", { class: "label" }, ["Evidence quality"]),
        el("div", { class: "value small" }, [
          `${(ep.quality_score ?? 0).toFixed(2)} `,
          el("span", { class: "pill gray" }, [ep.quality_label || "—"]),
        ]),
      ]),
      el("div", { class: "run-metric" }, [
        el("div", { class: "label" }, ["Face validity"]),
        el("div", { class: "value small" }, [
          el("span", { class: `pill ${fvBadgeClass(fvCls)}` }, [fv.status || "—"]),
        ]),
      ]),
      el("div", { class: "run-metric" }, [
        el("div", { class: "label" }, ["Review items"]),
        el("div", { class: "value" }, [String((run.review_queue || []).length)]),
      ]),
      el("div", { class: "run-metric" }, [
        el("div", { class: "label" }, ["Audit entries"]),
        el("div", { class: "value" }, [String((run.audit_log || []).length)]),
      ]),
    ]);

    const headBtns = el("div", { class: "quicklinks" }, [
      (() => { const b = el("button", null, ["🔍 Evidence Center"]); b.addEventListener("click", () => switchTab("evidence")); return b; })(),
      (() => { const b = el("button", null, ["✅ Review Queue"]); b.addEventListener("click", () => switchTab("review")); return b; })(),
    ]);

    const card = el("div", { class: "run-summary" }, [
      el("div", { class: "run-summary-header" }, [
        el("h3", null, ["Run Summary"]),
        headBtns,
      ]),
      metrics,
    ]);
    return card;
  }

  // ===================================================================
  // Store Readiness Dashboard (Manager View) — visual, scannable cards
  // built entirely from live readiness_summary / face_validity values.
  // ===================================================================
  function dashMeter(level) {
    // level: "ok" | "warn" | "err" | "gray"; returns a small bar element
    const pct = level === "err" ? 100 : level === "warn" ? 62 : level === "ok" ? 32 : 8;
    return el("div", { class: "dash-meter" }, [
      el("div", { class: `dash-meter-fill ${level}`, style: `width:${pct}%` }),
    ]);
  }

  function dashCard(opts) {
    // opts: {icon, label, level, value, detail, meter, note}
    const card = el("div", { class: `dash-card status-${opts.level || "gray"}` });
    card.appendChild(el("div", { class: "dash-card-head" }, [
      el("span", { class: "dash-icon" }, [opts.icon || "•"]),
      el("span", { class: "dash-label" }, [opts.label || ""]),
    ]));
    card.appendChild(el("div", { class: "dash-value" }, [opts.value != null ? String(opts.value) : "—"]));
    if (opts.meter) card.appendChild(dashMeter(opts.level || "gray"));
    if (opts.detail) card.appendChild(el("div", { class: "dash-detail" }, [opts.detail]));
    if (opts.note) card.appendChild(el("div", { class: "dash-note" }, [opts.note]));
    return card;
  }

  function readinessDashboard(run, rs) {
    const fv = run.face_validity || {};
    const ep = run.evidence_package || {};
    const wrap = el("div", { class: "readiness-dashboard" });

    // ── Header banner: overall readiness ──
    const overall = rs.overall_status || "unknown";
    const overallLevel = overall === "success" ? "ok"
      : overall === "needs_review" ? "review"
      : overall === "warning" ? "warn"
      : overall === "weak" || overall === "error" ? "err" : "gray";
    const overallText = overall === "success" ? "Store is ready to open"
      : overall === "warning" ? "Open with caution — review the flagged areas below"
      : overall === "needs_review" ? "Manager review recommended before opening"
      : "Readiness status unavailable for this input";
    wrap.appendChild(el("div", { class: `readiness-banner ${overallLevel}` }, [
      el("div", { class: "rb-left" }, [
        el("span", { class: "rb-icon" }, ["🏪"]),
        el("div", null, [
          el("div", { class: "rb-title" }, ["Store Readiness"]),
          el("div", { class: "rb-sub" }, [overallText]),
        ]),
      ]),
      el("span", { class: `pill ${overallLevel === "ok" ? "success" : overallLevel === "warn" ? "warning" : overallLevel === "review" ? "review" : overallLevel === "err" ? "error" : "gray"}` }, [overall]),
    ]));

    const grid = el("div", { class: "readiness-grid" });

    // ── Rush Risk ──
    const demandRisk = rs.demand_risk || "unknown";
    const hasForecast = rs.forecast_orders != null && Number(rs.forecast_orders) > 0;
    const rushLevel = demandRisk === "high" ? "err" : demandRisk === "medium" ? "warn" : demandRisk === "low" ? "ok" : "gray";
    grid.appendChild(dashCard({
      icon: "📈", label: "Rush Risk", level: rushLevel,
      value: (rs.demand_level && rs.demand_level !== "") ? rs.demand_level : "Unknown",
      detail: hasForecast ? `Risk: ${demandRisk} · forecast ${rs.forecast_orders} orders` : `Risk: ${demandRisk}`,
      meter: true,
      note: hasForecast ? null
        : "No demand forecast in the simulated data for this date, so rush risk is Unknown (not a system error). Forecasts cover specific dates such as 2024-01-15, 2024-01-22, 2024-01-29.",
    }));

    // ── Staffing ──
    const gap = rs.staffing_gap;
    let staffLevel = "gray", staffVal = "—", staffDetail = "";
    if (gap != null) {
      if (gap < -1) { staffLevel = "err"; staffVal = `Short ${Math.abs(gap)}`; staffDetail = "Understaffed — call in backup before opening."; }
      else if (gap < 0) { staffLevel = "warn"; staffVal = `Short ${Math.abs(gap)}`; staffDetail = "Slightly understaffed for this shift."; }
      else if (gap === 0) { staffLevel = "ok"; staffVal = "Balanced"; staffDetail = "Scheduled staff matches requirement."; }
      else { staffLevel = "ok"; staffVal = `+${gap} surplus`; staffDetail = "More staff scheduled than required."; }
    }
    grid.appendChild(dashCard({
      icon: "👥", label: "Staffing", level: staffLevel, value: staffVal, detail: staffDetail, meter: true,
    }));

    // ── Inventory Alerts ──
    const invUnavail = rs.inventory_unavailable_count || 0;
    const invLow = rs.inventory_low_count || 0;
    const invLevel = invUnavail > 0 ? "err" : invLow > 0 ? "warn" : "ok";
    const invVal = invUnavail > 0 ? `${invUnavail} unavailable` : invLow > 0 ? `${invLow} low` : "All clear";
    const invDetail = [];
    if (invUnavail > 0) invDetail.push(`${invUnavail} ingredient(s) unavailable`);
    if (invLow > 0) invDetail.push(`${invLow} low stock`);
    grid.appendChild(dashCard({
      icon: "📦", label: "Inventory Alerts", level: invLevel, value: invVal,
      detail: invDetail.length ? invDetail.join(" · ") : "Inventory sufficient for this shift.", meter: true,
    }));

    // ── Active Promotions ──
    const promo = rs.active_promotions_count || 0;
    grid.appendChild(dashCard({
      icon: "🏷️", label: "Active Promotions", level: promo > 0 ? "info" : "gray",
      value: promo, detail: promo > 0 ? "Brief baristas before the rush." : "No active promotions.",
    }));

    // ── Evidence Quality / Face Validity ──
    const fvLevel = fv.status === "plausible" ? "ok" : fv.status === "needs_review" ? "warn" : fv.status === "weak" ? "err" : "gray";
    grid.appendChild(dashCard({
      icon: "🎯", label: "Evidence / Face Validity", level: fvLevel,
      value: fv.status || "—",
      detail: `Quality ${(fv.evidence_quality?.score ?? ep.quality_score ?? 0)} · ${fv.evidence_quality?.label || ep.quality_label || "—"}`,
    }));

    wrap.appendChild(grid);
    return wrap;
  }

  // ── Manager-friendly Readiness Details ──────────────────────────────────────
  // Groups the live orchestrator output into skimmable sections. Only real
  // backend fields are used; missing fields are omitted (never fabricated).
  function fmtHour12(h) {
    if (h == null || h === "") return null;
    const n = Number(h);
    if (isNaN(n)) return null;
    const ampm = n < 12 ? "AM" : "PM";
    let hr = n % 12; if (hr === 0) hr = 12;
    return `${hr}:00 ${ampm}`;
  }
  function mgrBullet(text) { return el("li", null, [text]); }
  function mgrActionBullet(text) {
    return el("li", { class: "mgr-action" }, [el("strong", null, ["ACTION: "]), text]);
  }
  function mgrSection(title, bullets) {
    const real = bullets.filter(Boolean);
    if (!real.length) return null;
    const sec = el("div", { class: "mgr-section" });
    sec.appendChild(el("h4", { class: "mgr-section-title" }, [title]));
    const ul = el("ul", { class: "mgr-list" });
    real.forEach((b) => ul.appendChild(b));
    sec.appendChild(ul);
    return sec;
  }

  function managerBody(fo, run) {
    run = run || {};
    const body = el("div", { class: "mgr-readiness" });
    const addSection = (title, bullets) => { const s = mgrSection(title, bullets); if (s) body.appendChild(s); };
    const rs = fo.readiness_summary || {};
    const bg = fo.barista_guidance || {};
    const hourLabel = fmtHour12(fo.hour);

    // 1. Rush / Demand
    const demand = [];
    const dr = rs.demand_risk;
    const atHr = hourLabel ? ` at ${hourLabel}` : "";
    if (dr === "high") demand.push(mgrBullet(`High rush detected${atHr}.`));
    else if (dr === "medium") demand.push(mgrBullet(`Moderate rush expected${atHr}.`));
    else if (dr === "low") demand.push(mgrBullet(`Low rush expected${atHr}.`));
    else demand.push(mgrBullet("No demand forecast was returned for this date/time."));
    if (rs.demand_level) {
      demand.push(mgrBullet(`Forecasted demand is ${rs.demand_level.toLowerCase()}${rs.forecast_orders ? ` (~${rs.forecast_orders} orders).` : "."}`));
    }
    const dd = fo.demand_detail || {};
    if (dd.local_event_flag === "Yes" && dd.event_type) demand.push(mgrBullet(`Local event today: ${dd.event_type}.`));
    if (dd.weather_condition) demand.push(mgrBullet(`Weather: ${dd.weather_condition}.`));
    if (dr === "high") demand.push(mgrActionBullet("Ensure the espresso station is stocked and ready, and brief baristas to keep recommendations concise."));
    // No rush-reduction-time field is provided by the backend, so that line is omitted.
    addSection("☕ Rush / Demand", demand);

    // 2. Staffing
    const staff = [];
    const gap = rs.staffing_gap;
    const sd = fo.staffing_detail || {};
    if (gap != null && gap < 0) {
      staff.push(mgrBullet(`Staffing gap detected: ${sd.scheduled_staff ?? "?"} scheduled vs ${sd.required_staff ?? "?"} required (short ${Math.abs(gap)}).`));
      staff.push(mgrActionBullet("Reassign available staff or simplify customer recommendations during the rush window."));
    } else if (gap === 0 || rs.staffing_status === "Balanced") {
      staff.push(mgrBullet("Staffing is balanced — scheduled staff matches the requirement."));
    } else if (gap != null && gap > 0) {
      staff.push(mgrBullet(`Staffing surplus: ${gap} more than required.`));
    } else {
      staff.push(mgrBullet("No staffing detail was returned for this shift."));
    }
    if (sd.callout_count) staff.push(mgrBullet(`${sd.callout_count} staff callout(s) recorded for this window.`));
    addSection("👥 Staffing", staff);

    // 3. Inventory
    const inv = [];
    const unavail = (fo.inventory_unavailable || []).map((x) => x.ingredient || x).filter(Boolean);
    const low = (fo.inventory_low_stock || []).map((x) => x.ingredient || x).filter(Boolean);
    if (unavail.length) inv.push(mgrBullet(`Unavailable ingredient${unavail.length > 1 ? "s" : ""}: ${unavail.join(", ")}.`));
    if (low.length) inv.push(mgrBullet(`Low stock on ${low.join(", ")}.`));
    if (!unavail.length && !low.length) inv.push(mgrBullet("All ingredients are sufficient for this shift."));
    if (unavail.length || low.length) inv.push(mgrActionBullet("Reorder if possible and inform baristas before the rush."));
    addSection("📦 Inventory", inv);

    // 4. Promotions
    const promo = [];
    const promoItems = bg.promotion_items || [];
    const activePromos = fo.active_promotions || [];
    if (promoItems.length) {
      promo.push(mgrBullet(`Suggested promotion items: ${promoItems.join(", ")}.`));
      promo.push(mgrBullet("These are surfaced from active promotions and current inventory guidance."));
    } else if (activePromos.length) {
      promo.push(mgrBullet(`${activePromos.length} active promotion(s) for this shift.`));
    } else {
      promo.push(mgrBullet("No active promotions for this shift."));
    }
    const highRisk = activePromos.filter((p) => String(p.inventory_risk || "").toLowerCase() === "high").map((p) => p.item);
    if (highRisk.length) promo.push(mgrBullet(`High inventory-risk promo${highRisk.length > 1 ? "s" : ""}: ${highRisk.join(", ")}.`));
    if (promoItems.length || activePromos.length) promo.push(mgrActionBullet("Verify stock levels before actively promoting."));
    addSection("🏷️ Promotions", promo);

    // 5. Barista Guidance
    const guide = [];
    if (bg.service_mode === "concise" || bg.rush_level === "high") guide.push(mgrBullet("Keep recommendations concise during the rush."));
    if ((bg.avoid_ingredients || []).length) guide.push(mgrBullet(`Avoid unavailable ingredients: ${bg.avoid_ingredients.join(", ")}.`));
    if ((bg.caution_ingredients || []).length) guide.push(mgrBullet(`Use caution ingredients only if requested and available: ${bg.caution_ingredients.join(", ")}.`));
    if (guide.length) guide.push(mgrActionBullet("Brief baristas before peak traffic begins."));
    else guide.push(mgrBullet("No special barista guidance for this shift."));
    addSection("🧋 Barista Guidance", guide);

    // 6. Evidence / Face Validity (run-level fields)
    const ev = [];
    const ep = run.evidence_package || {};
    const fv = run.face_validity || {};
    if (ep.quality_label || ep.quality_score != null) {
      ev.push(mgrBullet(`Evidence quality: ${ep.quality_label || "—"}${ep.quality_score != null ? ` (${ep.quality_score}).` : "."}`));
    }
    if (fv.status) ev.push(mgrBullet(`Face validity status: ${fv.status}.`));
    if (fv.human_review_required) ev.push(mgrBullet("Human review recommended before this guidance is used."));
    const warns = run.warnings || [];
    if (warns.length) ev.push(mgrActionBullet(`Review the ${warns.length} warning(s) in the Evidence Center before endorsing shift guidance.`));
    addSection("🎯 Evidence / Face Validity", ev);

    // Technical Details — raw orchestrator fields, collapsed
    const techItems = [
      el("div", { class: "muted small" }, [
        `overall=${rs.overall_status ?? "—"} · demand=${rs.demand_risk ?? "—"} / ${rs.demand_level ?? "—"} · staffing_gap=${rs.staffing_gap ?? "—"} · inv_unavailable=${rs.inventory_unavailable_count ?? "—"} · inv_low=${rs.inventory_low_count ?? "—"} · promos=${rs.active_promotions_count ?? "—"} · forecast=${rs.forecast_orders ?? "—"}`,
      ]),
    ];
    const rawActions = fo.recommended_actions || [];
    if (rawActions.length) {
      const ul = el("ul", { class: "mgr-list" });
      rawActions.forEach((a) => ul.appendChild(el("li", { class: "muted small" }, [a])));
      techItems.push(el("div", { class: "muted small", style: "margin-top:8px;font-weight:600" }, ["Raw recommended_actions:"]));
      techItems.push(ul);
    }
    body.appendChild(el("details", { class: "mgr-tech" }, [
      el("summary", null, ["⚙️ Technical details (raw orchestrator fields)"]),
      el("div", { class: "mgr-tech-body" }, techItems),
    ]));

    return body;
  }

  function recBody(fo) {
    const body = el("div");
    if (fo.customer_request) body.appendChild(el("div", null, [el("strong", null, ["Customer request: "]), fo.customer_request]));
    const prefs = fo.preferences || {};
    if (Object.keys(prefs).length) body.appendChild(el("div", { class: "muted small" }, [el("strong", null, ["Inferred preferences: "]), JSON.stringify(prefs)]));
    const cands = fo.top_candidates || [];
    if (cands.length) {
      body.appendChild(el("h4", null, [`Top candidates (${cands.length})`]));
      const ul = el("ul", null);
      cands.forEach((c) => {
        const li = el("li", null, [
          el("strong", null, [c.item || "(unknown)"]),
          ` — ${c.category || ""} (score ${Number(c.score || 0).toFixed(2)})`,
        ]);
        if (c.reason_codes?.length) li.appendChild(el("div", { class: "muted small" }, [`reasons: ${c.reason_codes.join(", ")}`]));
        ul.appendChild(li);
      });
      body.appendChild(ul);
    }
    return body;
  }

  function orderBody(fo) {
    const body = el("div");
    if (fo.raw_order) body.appendChild(el("div", { class: "muted small" }, [el("strong", null, ["Raw order: "]), fo.raw_order]));
    const so = fo.structured_order || {};
    body.appendChild(el("h4", null, ["Structured order"]));
    Object.entries(so).forEach(([k, v]) => body.appendChild(el("div", { class: "muted small" }, [el("strong", null, [`${k}: `]), Array.isArray(v) ? v.join(", ") : String(v ?? "—")])));
    if (fo.missing_fields?.length) {
      body.appendChild(el("div", { class: "status-banner review" }, [el("strong", null, ["Missing fields: "]), fo.missing_fields.join(", ")]));
    }
    if (fo.follow_up_question) {
      body.appendChild(el("div", null, [el("strong", null, ["Follow-up: "]), fo.follow_up_question]));
    }
    if (fo.prep_notes?.length) {
      body.appendChild(el("h4", null, ["Prep notes"]));
      const ul = el("ul", null);
      fo.prep_notes.forEach((p) => ul.appendChild(el("li", null, [p])));
      body.appendChild(ul);
    }
    return body;
  }

  function renderWorkflow(targetId, run, opts) {
    const root = document.getElementById(targetId);
    root.innerHTML = "";
    if (!run) return;
    if (run.error) {
      root.appendChild(el("div", { class: "status-banner err" }, [el("strong", null, ["Error: "]), run.error]));
      return;
    }

    root.appendChild(statusBanner(run.status));
    root.appendChild(runSummaryCard(run));
    // Compact summary strip immediately after the run summary; full details
    // are available in the collapsible panel at the bottom of the output.
    const fvStrip = faceValiditySummary(run.face_validity);
    if (fvStrip) root.appendChild(fvStrip);

    const wf = run.workflow_type;
    const fo = run.final_output || {};

    if (wf === "manager_readiness") {
      root.appendChild(readinessDashboard(run, fo.readiness_summary || {}));
      root.appendChild(outCard("👤 Readiness Details", managerBody(fo, run), true));
    } else if (wf === "barista_recommendation") {
      root.appendChild(outCard("🧋 Recommendation", recBody(fo), true));
    } else if (wf === "order_builder") {
      root.appendChild(outCard("📝 Order Builder", orderBody(fo), true));
    } else if (wf === "full_workflow") {
      if (fo.manager_readiness) {
        root.appendChild(readinessDashboard(run, fo.manager_readiness.readiness_summary || {}));
        root.appendChild(outCard("👤 Readiness Details", managerBody(fo.manager_readiness, run), false));
      }
      if (fo.recommendation)    root.appendChild(outCard("🧋 Recommendation",    recBody(fo.recommendation),    true));
      if (fo.order)             root.appendChild(outCard("📝 Order Builder",     orderBody(fo.order),           true));
      else                       root.appendChild(el("div", { class: "muted small" }, ["Order phase skipped — no raw_order provided."]));
    }

    // Workflow-level review actions
    const reviewBody = el("div", null, [
      el("p", { class: "muted small" }, ["Approve, edit, reject, or escalate the workflow output as a whole. Actions append to the Audit Log; no DB writes."]),
      reviewActionButtons(`${run.workflow_type}#workflow`, run.workflow_type),
    ]);
    root.appendChild(outCard("✅ Workflow-level Review", reviewBody, true));

    // Face Validity collapsible details — collapsed by default, full detail
    const fvCollapsible = faceValidityCollapsible(run.face_validity);
    if (fvCollapsible) root.appendChild(fvCollapsible);

    // Raw JSON (closed by default)
    const raw = el("div", null, [el("pre", { class: "json" }, [JSON.stringify(run, null, 2)])]);
    root.appendChild(outCard(`Raw orchestrator JSON · run_id=${run.run_id || "—"}`, raw, false));
  }

  // ===================================================================
  // Progress tracker (Full Workflow)
  // ===================================================================
  function updateProgress(run) {
    const tracker = document.getElementById("full-progress");
    if (!tracker) return;
    const phases = new Set((run.steps || []).map((s) => s.phase).filter(Boolean));
    tracker.querySelectorAll(".step").forEach((s) => {
      s.classList.remove("active", "done");
      const phase = s.dataset.step;
      if (phase === "input") s.classList.add("done");
      else if (phase === "complete") s.classList.add("done");
      else if (phases.has(phase)) s.classList.add("done");
    });
  }

  // ===================================================================
  // Sidebar badge counts + foot run-id
  // ===================================================================
  function updateSidebarBadges(run) {
    const evi = document.getElementById("evi-count");
    const rev = document.getElementById("rev-count");
    const foot = document.getElementById("foot-runid");
    if (!run) {
      evi.hidden = true; rev.hidden = true;
      foot.textContent = "No active run";
      return;
    }
    const eviCount = run.evidence_package?.evidence_count || 0;
    const revCount = (run.review_queue || []).length;
    evi.textContent = eviCount; evi.hidden = eviCount === 0;
    rev.textContent = revCount; rev.hidden = revCount === 0;
    foot.textContent = run.run_id || run.workflow_type || "—";
  }

  function storeLastRun(run) {
    window.__lastRun = run;
    renderEvidenceCenter(run);
    renderReviewQueue(run);
    updateSidebarBadges(run);
  }

  // ===================================================================
  // Flash banner
  // ===================================================================
  function flashBanner(msg, kind) {
    const b = el("div", { class: `status-banner flash ${kind || "ok"}` }, [msg]);
    document.body.appendChild(b);
    setTimeout(() => b.remove(), 3500);
  }
  // Expose helpers the inline script (index.html) relies on. Without this the
  // inline queue code throws ReferenceError on flashBanner/refreshAudit, which
  // previously aborted the Done/Add handlers before they could refresh the UI.
  window.flashBanner = flashBanner;

  // ===================================================================
  // Daily Dashboard renderer
  // ===================================================================

  // Inline SVG meter (0–100 pct, colored by level)
  function svgMeter(pct, level, label) {
    const color = level === "err" ? "var(--error)" : level === "warn" ? "var(--warning)" : level === "ok" ? "var(--success)" : "var(--neutral-400)";
    const w = 200, h = 14, r = h / 2;
    return el("div", { class: "dd-meter-wrap" }, [
      el("div", { class: "dd-meter-label" }, [label || ""]),
      el("svg", null, []), // replaced below with innerHTML
    ]);
    // use innerHTML for SVG (el() can't create SVG elements directly)
  }

  function makeSVGMeter(pct, level) {
    const color = level === "err" ? "#DC2626" : level === "warn" ? "#D97706" : level === "ok" ? "#2F7D52" : "#A3A3A3";
    const w = 220, h = 12;
    const fill = Math.max(2, Math.round(pct * w / 100));
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
    svg.setAttribute("width", "100%");
    svg.setAttribute("height", String(h));
    svg.style.display = "block";
    const bg = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    bg.setAttribute("x", "0"); bg.setAttribute("y", "0");
    bg.setAttribute("width", String(w)); bg.setAttribute("height", String(h));
    bg.setAttribute("rx", String(h / 2)); bg.setAttribute("fill", "#E5E5E5");
    const bar = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    bar.setAttribute("x", "0"); bar.setAttribute("y", "0");
    bar.setAttribute("width", String(fill)); bar.setAttribute("height", String(h));
    bar.setAttribute("rx", String(h / 2)); bar.setAttribute("fill", color);
    svg.appendChild(bg); svg.appendChild(bar);
    return svg;
  }

  function ddMetricCard(icon, label, value, level) {
    const cls = level === "err" ? "status-err" : level === "warn" ? "status-warn" : level === "ok" ? "status-ok" : "status-gray";
    const pill = level === "err" ? "error" : level === "warn" ? "warning" : level === "ok" ? "success" : "gray";
    const card = el("div", { class: `dd-metric-card ${cls}` });
    card.appendChild(el("div", { class: "dd-metric-icon" }, [icon]));
    card.appendChild(el("div", { class: "dd-metric-label" }, [label]));
    card.appendChild(el("div", { class: "dd-metric-value" }, [String(value ?? "—")]));
    return card;
  }

  function renderDailyDashboard(run) {
    const fo = run.final_output || {};
    const rs = fo.readiness_summary || {};
    const bg = fo.barista_guidance || {};
    const ep = run.evidence_package || {};
    const fv = run.face_validity || {};
    const queuedCount = (document.getElementById("oq-count") || {}).textContent || "0";
    const completedCount = (document.querySelectorAll ? document.querySelectorAll(".completed-item").length : 0);
    const reviewCount = (run.review_queue || []).length;

    document.getElementById("dash-empty").hidden = true;
    document.getElementById("dash-populated").hidden = false;

    // ── Metric cards row ──────────────────────────────────────────────
    const rushLevel = rs.demand_risk === "high" ? "err" : rs.demand_risk === "medium" ? "warn" : rs.demand_risk === "low" ? "ok" : "gray";
    const invLevel = (rs.inventory_unavailable_count || 0) > 0 ? "err" : (rs.inventory_low_count || 0) > 0 ? "warn" : "ok";
    const staffGap = rs.staffing_gap;
    const staffLevel = (staffGap != null && staffGap < 0) ? "err" : (staffGap != null && staffGap === 0) ? "ok" : (staffGap != null && staffGap > 0) ? "ok" : "gray";
    const fvLevel = fv.status === "plausible" ? "ok" : fv.status === "needs_review" ? "warn" : fv.status === "weak" ? "err" : "gray";

    const row = document.getElementById("dd-metric-row");
    row.innerHTML = "";
    row.appendChild(ddMetricCard("📈", "Rush Risk", (rs.demand_level && rs.demand_level !== "") ? rs.demand_level : (rs.demand_risk || "Unknown"), rushLevel));
    row.appendChild(ddMetricCard("👥", "Staffing", staffGap != null ? (staffGap < 0 ? `Short ${Math.abs(staffGap)}` : staffGap === 0 ? "Balanced" : `+${staffGap} surplus`) : "—", staffLevel));
    row.appendChild(ddMetricCard("📦", "Inventory Alerts", (rs.inventory_unavailable_count || 0) + (rs.inventory_low_count || 0) + " flagged", invLevel));
    row.appendChild(ddMetricCard("🎯", "Orders Queued", queuedCount, queuedCount === "0" || queuedCount === 0 ? "gray" : "ok"));
    row.appendChild(ddMetricCard("✅", "Orders Completed", String(completedCount), completedCount > 0 ? "ok" : "gray"));
    row.appendChild(ddMetricCard("🔍", "Review Items", String(reviewCount), reviewCount > 0 ? "warn" : "ok"));
    row.appendChild(ddMetricCard("🎯", "Face Validity", fv.status || "—", fvLevel));

    // ── Charts grid ───────────────────────────────────────────────────
    const grid = document.getElementById("dd-charts-grid");
    grid.innerHTML = "";

    // A. Rush meter
    const rushPct = rs.demand_risk === "high" ? 95 : rs.demand_risk === "medium" ? 60 : rs.demand_risk === "low" ? 25 : 5;
    const dd = fo.demand_detail || {};
    const rushCard = el("div", { class: "dd-chart-card" });
    rushCard.appendChild(el("h4", { class: "dd-chart-title" }, ["📈 Rush / Demand"]));
    rushCard.appendChild(el("div", { class: "dd-chart-subtitle" }, [
      rs.demand_level ? `${rs.demand_level}${rs.forecast_orders ? ` · ~${rs.forecast_orders} forecast orders` : ""}` : "No forecast for this date",
    ]));
    rushCard.appendChild(makeSVGMeter(rushPct, rushLevel));
    if (dd.weather_condition) rushCard.appendChild(el("div", { class: "dd-chart-note" }, [`☁️ ${dd.weather_condition}${dd.local_event_flag === "Yes" && dd.event_type ? " · " + dd.event_type : ""}`]));
    if (!rs.forecast_orders) rushCard.appendChild(el("div", { class: "dd-no-data" }, ["No demand forecast in simulated data for this date."]));
    grid.appendChild(rushCard);

    // B. Staffing
    const sd = fo.staffing_detail || {};
    const req = sd.required_staff || rs.staffing_gap != null ? (rs.staffing_gap + (sd.scheduled_staff || 0)) : null;
    const sch = sd.scheduled_staff;
    const staffCard = el("div", { class: "dd-chart-card" });
    staffCard.appendChild(el("h4", { class: "dd-chart-title" }, ["👥 Staffing"]));
    if (sch != null && sd.required_staff != null) {
      const maxS = Math.max(sch, sd.required_staff, 1);
      staffCard.appendChild(el("div", { class: "dd-stacked-bars" }, [
        el("div", { class: "dd-bar-row" }, [
          el("span", { class: "dd-bar-label" }, ["Required"]),
          el("div", { class: "dd-bar-track" }, [
            el("div", { class: `dd-bar-fill ${staffGap != null && staffGap < 0 ? "err" : "ok"}`, style: `width:${Math.round(sd.required_staff / maxS * 100)}%` }),
          ]),
          el("span", { class: "dd-bar-val" }, [String(sd.required_staff)]),
        ]),
        el("div", { class: "dd-bar-row" }, [
          el("span", { class: "dd-bar-label" }, ["Scheduled"]),
          el("div", { class: "dd-bar-track" }, [
            el("div", { class: `dd-bar-fill ${staffLevel}`, style: `width:${Math.round(sch / maxS * 100)}%` }),
          ]),
          el("span", { class: "dd-bar-val" }, [String(sch)]),
        ]),
      ]));
      staffCard.appendChild(el("div", { class: "dd-chart-note" }, [rs.staffing_status || (staffGap === 0 ? "Balanced" : staffGap < 0 ? `Understaffed by ${Math.abs(staffGap)}` : `Surplus of ${staffGap}`)]));
    } else {
      staffCard.appendChild(el("div", { class: "dd-no-data" }, ["No staffing detail returned for this shift."]));
    }
    grid.appendChild(staffCard);

    // C. Inventory
    const unavailItems = (fo.inventory_unavailable || []).map((x) => x.ingredient || x).filter(Boolean);
    const lowItems = (fo.inventory_low_stock || []).map((x) => x.ingredient || x).filter(Boolean);
    const totalItems = unavailItems.length + lowItems.length;
    const invCard = el("div", { class: "dd-chart-card" });
    invCard.appendChild(el("h4", { class: "dd-chart-title" }, ["📦 Inventory"]));
    if (unavailItems.length || lowItems.length) {
      const pct = Math.min(100, Math.round(totalItems / 10 * 100));
      invCard.appendChild(makeSVGMeter(pct, invLevel));
      if (unavailItems.length) {
        invCard.appendChild(el("div", { class: "dd-inv-row err" }, [el("strong", null, ["Unavailable: "]), unavailItems.join(", ")]));
      }
      if (lowItems.length) {
        invCard.appendChild(el("div", { class: "dd-inv-row warn" }, [el("strong", null, ["Low stock: "]), lowItems.slice(0, 5).join(", ") + (lowItems.length > 5 ? ` +${lowItems.length - 5} more` : "")]));
      }
    } else {
      invCard.appendChild(makeSVGMeter(5, "ok"));
      invCard.appendChild(el("div", { class: "dd-chart-note" }, ["All ingredients sufficient."]));
    }
    grid.appendChild(invCard);

    // D. Orders (from UI state — not backend)
    const ordCard = el("div", { class: "dd-chart-card" });
    ordCard.appendChild(el("h4", { class: "dd-chart-title" }, ["🎯 Orders"]));
    const qN = parseInt(queuedCount, 10) || 0;
    const cN = completedCount;
    if (qN + cN === 0) {
      ordCard.appendChild(el("div", { class: "dd-no-data" }, ["Orders will appear here after running Barista or Order Builder workflows."]));
    } else {
      const total = qN + cN || 1;
      ordCard.appendChild(el("div", { class: "dd-stacked-bars" }, [
        el("div", { class: "dd-bar-row" }, [
          el("span", { class: "dd-bar-label" }, ["Queued"]),
          el("div", { class: "dd-bar-track" }, [el("div", { class: "dd-bar-fill warn", style: `width:${Math.round(qN / total * 100)}%` })]),
          el("span", { class: "dd-bar-val" }, [String(qN)]),
        ]),
        el("div", { class: "dd-bar-row" }, [
          el("span", { class: "dd-bar-label" }, ["Completed"]),
          el("div", { class: "dd-bar-track" }, [el("div", { class: "dd-bar-fill ok", style: `width:${Math.round(cN / total * 100)}%` })]),
          el("span", { class: "dd-bar-val" }, [String(cN)]),
        ]),
        el("div", { class: "dd-bar-row" }, [
          el("span", { class: "dd-bar-label" }, ["Review"]),
          el("div", { class: "dd-bar-track" }, [el("div", { class: `dd-bar-fill ${reviewCount > 0 ? "warn" : "ok"}`, style: `width:${reviewCount > 0 ? "20%" : "5%"}` })]),
          el("span", { class: "dd-bar-val" }, [String(reviewCount)]),
        ]),
      ]));
    }
    grid.appendChild(ordCard);

    // E. Evidence / Face Validity traffic-light
    const evCard = el("div", { class: "dd-chart-card" });
    evCard.appendChild(el("h4", { class: "dd-chart-title" }, ["🎯 Evidence & Validity"]));
    const tl = el("div", { class: "dd-traffic-light" });
    ["plausible", "needs_review", "weak"].forEach((s) => {
      const active = fv.status === s;
      const lv = s === "plausible" ? "ok" : s === "needs_review" ? "warn" : "err";
      const dot = el("div", { class: `dd-tl-dot ${lv}${active ? " active" : ""}` });
      tl.appendChild(dot);
    });
    if (!fv.status) tl.appendChild(el("div", { class: "dd-tl-dot gray active" }));
    evCard.appendChild(tl);
    evCard.appendChild(el("div", { class: "dd-chart-subtitle" }, [fv.status ? `${fv.status}` : "No run yet"]));
    if (ep.quality_label) evCard.appendChild(el("div", { class: "dd-chart-note" }, [`Quality: ${ep.quality_label} (${(ep.quality_score || 0).toFixed(2)}) · ${ep.evidence_count || 0} items`]));
    const ragCount = (ep.rag_results || ep.rag_snippets || []).length;
    const toolCount = (ep.tool_outputs || []).length;
    if (ragCount || toolCount) evCard.appendChild(el("div", { class: "dd-chart-note" }, [`${toolCount} tool outputs · ${ragCount} RAG documents`]));
    grid.appendChild(evCard);

    // ── Written summary cards ─────────────────────────────────────────
    const sumRoot = document.getElementById("dd-summary-cards");
    sumRoot.innerHTML = "";

    // Manager Actions
    const actions = fo.recommended_actions || [];
    if (actions.length) {
      const ac = el("div", { class: "card" });
      ac.appendChild(el("h3", null, ["📋 Recommended Manager Actions"]));
      const ul = el("ul", { class: "mgr-list" });
      actions.forEach((a) => ul.appendChild(el("li", null, [a])));
      ac.appendChild(ul);
      sumRoot.appendChild(ac);
    }

    // Barista Guidance
    if (Object.keys(bg).length) {
      const bc = el("div", { class: "card" });
      bc.appendChild(el("h3", null, ["🧋 Barista Guidance"]));
      const ul = el("ul", { class: "mgr-list" });
      if (bg.rush_level) ul.appendChild(el("li", null, [`Rush level: ${bg.rush_level} · Service mode: ${bg.service_mode || "—"}`]));
      if ((bg.avoid_ingredients || []).length) ul.appendChild(el("li", null, [`Avoid: ${bg.avoid_ingredients.join(", ")}`]));
      if ((bg.caution_ingredients || []).length) ul.appendChild(el("li", null, [`Use with caution: ${bg.caution_ingredients.join(", ")}`]));
      if ((bg.promotion_items || []).length) ul.appendChild(el("li", null, [`Promotion items: ${bg.promotion_items.join(", ")}`]));
      bc.appendChild(ul);
      sumRoot.appendChild(bc);
    }
  }

  // Daily Summary run button — calls run_manager_readiness and populates dashboard
  const runDashBtn = document.getElementById("run-dash");
  if (runDashBtn) {
    runDashBtn.addEventListener("click", async (e) => {
      const storeEl = document.getElementById("dash-store");
      const dateEl = document.getElementById("dash-date");
      const hourEl = document.getElementById("dash-hour");
      let valid = true;
      [["dash-store", storeEl], ["dash-date", dateEl], ["dash-hour", hourEl]].forEach(([id, el]) => {
        if (!el || !(el.value || "").trim()) { setFieldError(id, "Required."); valid = false; }
        else clearFieldError(id);
      });
      if (!valid) return;
      const btn = e.currentTarget; btn.disabled = true;
      try {
        const body = {
          store_id: storeEl.value,
          date: dateEl.value || "2024-01-15",
          hour: Number(hourEl.value),
        };
        const { ok, data } = await postJSON("/api/manager_readiness", body);
        if (!ok) { flashBanner("Daily Summary failed: " + (data.error || ""), "err"); return; }
        renderDailyDashboard(data);
        storeLastRun(data);
        await refreshAudit();
      } finally { btn.disabled = false; }
    });
  }

  // ===================================================================
  // Workflow run buttons
  // ===================================================================
  function hideEmpty(id) { const e = document.getElementById(id); if (e) e.hidden = true; }

  document.getElementById("run-manager").addEventListener("click", async (e) => {
    if (!validateFields(["mgr-store", "mgr-date", "mgr-hour"])) return;
    const btn = e.currentTarget; btn.disabled = true;
    try {
      const body = {
        store_id: document.getElementById("mgr-store").value,
        date: document.getElementById("mgr-date").value || "2024-01-15",
        hour: Number(document.getElementById("mgr-hour").value),
      };
      const { ok, data } = await postJSON("/api/manager_readiness", body);
      if (!ok) flashBanner("Manager readiness failed: " + (data.error || ""), "err");
      hideEmpty("manager-empty");
      renderWorkflow("manager-output", data);
      storeLastRun(data);
      await refreshAudit();
    } finally { btn.disabled = false; }
  });

  // ===================================================================
  // Barista View helpers
  // ===================================================================

  function barCtx() {
    return {
      store_id: (document.getElementById("bar-store") || {}).value || "",
      date: (document.getElementById("bar-date") || {}).value || "2024-01-15",
      hour: Number((document.getElementById("bar-hour") || {}).value || 8),
    };
  }

  function hasBarRecInput() {
    const req = ((document.getElementById("bar-request") || {}).value || "").trim();
    const prefs = readPrefs("bar");
    const hasChips = document.querySelectorAll(".pref-chip.active, .refine-chip.active").length > 0;
    return !!(req || prefs || hasChips);
  }

  function hasBarOrderInput() {
    return !!((document.getElementById("bar-raworder") || {}).value || "").trim();
  }

  // Render the barista briefing panel from a manager_readiness run
  function renderBaristaBriefing(run) {
    const empty = document.getElementById("bar-briefing-empty");
    const content = document.getElementById("bar-briefing-content");
    if (!run || !content) return;
    if (empty) empty.hidden = true;
    content.hidden = false;
    content.innerHTML = "";

    const fo = run.final_output || {};
    const rs = fo.readiness_summary || {};
    const bg = fo.barista_guidance || {};

    function briefCard(level, icon, title, bullets) {
      if (!bullets.filter(Boolean).length) return null;
      const card = el("div", { class: `brief-card brief-${level}` });
      card.appendChild(el("div", { class: "brief-card-head" }, [
        el("span", { class: "brief-icon" }, [icon]),
        el("span", { class: "brief-title" }, [title]),
      ]));
      const ul = el("ul", { class: "brief-list" });
      bullets.filter(Boolean).forEach((b) => ul.appendChild(el("li", null, [b])));
      card.appendChild(ul);
      return card;
    }

    // Rush Risk
    const dr = rs.demand_risk || "unknown";
    const rushLevel = dr === "high" ? "err" : dr === "medium" ? "warn" : "ok";
    const rushCard = briefCard(rushLevel, "📈", "Rush Risk", [
      dr !== "unknown" ? `${(rs.demand_level || dr).replace(/_/g," ")}${rs.forecast_orders ? ` · ~${rs.forecast_orders} orders forecast` : ""}` : "No demand forecast for this date.",
    ]);
    if (rushCard) content.appendChild(rushCard);

    // Inventory Alerts
    const unavail = (fo.inventory_unavailable || []).map((x) => x.ingredient || x).filter(Boolean);
    const low = (fo.inventory_low_stock || []).map((x) => x.ingredient || x).filter(Boolean);
    const invBullets = [];
    if (unavail.length) invBullets.push(`🚫 Unavailable: ${unavail.join(", ")}`);
    if (low.length) invBullets.push(`⚠️ Low stock: ${low.slice(0, 5).join(", ")}${low.length > 5 ? ` +${low.length - 5} more` : ""}`);
    if (!invBullets.length) invBullets.push("✅ All ingredients sufficient.");
    const invLevel = unavail.length ? "err" : low.length ? "warn" : "ok";
    const invCard = briefCard(invLevel, "📦", "Inventory Alerts", invBullets);
    if (invCard) content.appendChild(invCard);

    // Promote / Feature
    const promoItems = bg.promotion_items || [];
    if (promoItems.length) {
      const pc = briefCard("info", "🏷️", "Promote Today", [
        `Feature: ${promoItems.join(", ")}`,
        "Verify stock before actively promoting.",
      ]);
      if (pc) content.appendChild(pc);
    }

    // Avoid / Use Caution
    const avoid = bg.avoid_ingredients || [];
    const caution = bg.caution_ingredients || [];
    const avoidBullets = [];
    if (avoid.length) avoidBullets.push(`🚫 Avoid: ${avoid.join(", ")}`);
    if (caution.length) avoidBullets.push(`⚠️ Use with caution: ${caution.join(", ")}`);
    if (avoidBullets.length) {
      const ac = briefCard("warn", "⚠️", "Avoid / Use Caution", avoidBullets);
      if (ac) content.appendChild(ac);
    }

    // Action Guidance (from recommended_actions, filtered to barista-relevant ones)
    const actions = (fo.recommended_actions || []).filter((a) =>
      /espresso|barista|rush|concise|stock|recommend/i.test(a)
    );
    if (actions.length) {
      const agCard = briefCard("info", "💡", "Action Guidance", actions.slice(0, 3));
      if (agCard) content.appendChild(agCard);
    }

    // Timestamp note
    content.appendChild(el("div", { class: "brief-timestamp muted small" }, [
      `Loaded at ${new Date().toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"})} · run_id=${run.run_id || "—"}`,
    ]));
  }

  // ── Load Barista Briefing ──────────────────────────────────────────
  const loadBriefingBtn = document.getElementById("load-briefing");
  if (loadBriefingBtn) {
    loadBriefingBtn.addEventListener("click", async (e) => {
      if (!validateFields(["bar-store", "bar-date", "bar-hour"])) return;
      const btn = e.currentTarget; btn.disabled = true;
      try {
        const ctx = barCtx();
        const { ok, data } = await postJSON("/api/manager_readiness", ctx);
        if (!ok) { flashBanner("Briefing failed: " + (data.error || ""), "err"); return; }
        renderBaristaBriefing(data);
        flashBanner("Barista briefing loaded.", "ok");
      } finally { btn.disabled = false; }
    });
  }

  // ── Recommend Drink ───────────────────────────────────────────────
  document.getElementById("run-barista").addEventListener("click", async (e) => {
    if (!validateFields(["bar-store", "bar-date", "bar-hour"])) return;
    const btn = e.currentTarget; btn.disabled = true;
    try {
      const ctx = barCtx();
      const body = {
        ...ctx,
        customer_request: (document.getElementById("bar-request") || {}).value || "",
        preferences: readPrefs("bar"),
      };
      const { ok, data } = await postJSON("/api/barista_recommendation", body);
      if (!ok) flashBanner("Recommendation failed: " + (data.error || ""), "err");
      hideEmpty("barista-empty");
      document.getElementById("barista-order-output").innerHTML = "";
      renderWorkflow("barista-output", data);
      storeLastRun(data);
      await refreshAudit();
    } finally { btn.disabled = false; }
  });

  // ── Build Final Order ─────────────────────────────────────────────
  const runBaristaOrder = document.getElementById("run-barista-order");
  if (runBaristaOrder) {
    runBaristaOrder.addEventListener("click", async (e) => {
      if (!validateFields(["bar-store", "bar-date", "bar-hour"])) return;
      const rawOrder = ((document.getElementById("bar-raworder") || {}).value || "").trim();
      if (!rawOrder) {
        setFieldError("bar-raworder", "Please enter a raw final order to build.");
        document.getElementById("bar-raworder").scrollIntoView({ behavior: "smooth", block: "center" });
        return;
      }
      clearFieldError("bar-raworder");
      // Prepend selected size to raw order if raw order doesn't already contain a size word.
      // This gives the backend a size hint without overriding text the user already typed.
      const selSize = ((document.getElementById("bar-pref-size") || {}).value || "").trim();
      const sizeWords = ["short", "tall", "grande", "venti", "trenta"];
      const rawLower = rawOrder.toLowerCase();
      const sizeInRaw = sizeWords.some((s) => rawLower.includes(s));
      const effectiveRaw = (selSize && !sizeInRaw) ? `${selSize} ${rawOrder}` : rawOrder;
      const btn = e.currentTarget; btn.disabled = true;
      try {
        const ctx = barCtx();
        const body = { store_id: ctx.store_id, date: ctx.date, raw_order: effectiveRaw };
        const { ok, data } = await postJSON("/api/order_builder", body);
        if (!ok) flashBanner("Order build failed: " + (data.error || ""), "err");
        hideEmpty("barista-empty");
        document.getElementById("barista-output").innerHTML = "";
        // Reset injection guard so the new render gets a fresh "Add to Orders" button
        const orderOut = document.getElementById("barista-order-output");
        if (orderOut) delete orderOut.dataset.addOrdersInjected;
        window.__lastOrderBuild = data;
        renderWorkflow("barista-order-output", data);
        storeLastRun(data);
        await refreshAudit();
      } finally { btn.disabled = false; }
    });
  }

  // ── Recommend + Build Order ───────────────────────────────────────
  const runBaristaBoth = document.getElementById("run-barista-both");
  if (runBaristaBoth) {
    runBaristaBoth.addEventListener("click", async (e) => {
      if (!validateFields(["bar-store", "bar-date", "bar-hour"])) return;
      const hasRec = hasBarRecInput();
      const hasOrd = hasBarOrderInput();
      if (!hasRec && !hasOrd) {
        flashBanner("Please enter a customer request, select preferences, or provide a raw final order.", "warn");
        return;
      }
      const btn = e.currentTarget; btn.disabled = true;
      try {
        const ctx = barCtx();
        hideEmpty("barista-empty");

        // Run recommendation if rec input exists
        if (hasRec) {
          const recBody = {
            ...ctx,
            customer_request: (document.getElementById("bar-request") || {}).value || "",
            preferences: readPrefs("bar"),
          };
          const { ok: rok, data: rdata } = await postJSON("/api/barista_recommendation", recBody);
          if (!rok) flashBanner("Recommendation failed: " + (rdata.error || ""), "err");
          else { renderWorkflow("barista-output", rdata); storeLastRun(rdata); }
        } else {
          document.getElementById("barista-output").innerHTML = "";
        }

        // Run order builder if raw order exists
        if (hasOrd) {
          const rawOrder = document.getElementById("bar-raworder").value.trim();
          const sSize = ((document.getElementById("bar-pref-size") || {}).value || "").trim();
          const szWords = ["short","tall","grande","venti","trenta"];
          const sizePresent = szWords.some((s) => rawOrder.toLowerCase().includes(s));
          const finalRaw = (sSize && !sizePresent) ? `${sSize} ${rawOrder}` : rawOrder;
          const ordBody = { store_id: ctx.store_id, date: ctx.date, raw_order: finalRaw };
          const { ok: ook, data: odata } = await postJSON("/api/order_builder", ordBody);
          if (!ook) flashBanner("Order build failed: " + (odata.error || ""), "err");
          else {
            const oo = document.getElementById("barista-order-output");
            if (oo) delete oo.dataset.addOrdersInjected;
            window.__lastOrderBuild = odata;
            renderWorkflow("barista-order-output", odata);
            storeLastRun(odata);
          }
        } else {
          document.getElementById("barista-order-output").innerHTML = "";
          if (hasRec) flashBanner("Recommendation ready. Enter a raw final order to also build it.", "ok");
        }

        await refreshAudit();
      } finally { btn.disabled = false; }
    });
  }

  document.getElementById("run-order").addEventListener("click", async (e) => {
    if (!validateFields(["ord-store", "ord-date", "ord-raw"])) return;
    const btn = e.currentTarget; btn.disabled = true;
    try {
      const body = {
        store_id: document.getElementById("ord-store").value,
        date: document.getElementById("ord-date").value || "2024-01-15",
        raw_order: document.getElementById("ord-raw").value || "",
      };
      const { ok, data } = await postJSON("/api/order_builder", body);
      if (!ok) flashBanner("Order builder failed: " + (data.error || ""), "err");
      hideEmpty("order-empty");
      renderWorkflow("order-output", data);
      storeLastRun(data);
      await refreshAudit();
    } finally { btn.disabled = false; }
  });

  document.getElementById("run-full").addEventListener("click", async (e) => {
    if (!validateFields(["full-store", "full-date", "full-hour"])) return;
    // Customer Request is optional as long as another input source is present:
    // structured preferences or a raw order.
    const fullRequest = (document.getElementById("full-request").value || "").trim();
    const fullRaw = (document.getElementById("full-raworder").value || "").trim();
    const fullPrefs = readPrefs("full");
    if (!fullRequest && !fullRaw && !fullPrefs) {
      setFieldError("full-request", "Please enter a customer request, select preferences, or provide a raw order.");
      return;
    }
    clearFieldError("full-request");
    const btn = e.currentTarget; btn.disabled = true;
    try {
      const body = {
        store_id: document.getElementById("full-store").value,
        date: document.getElementById("full-date").value || "2024-01-15",
        hour: Number(document.getElementById("full-hour").value),
        customer_request: document.getElementById("full-request").value || "",
        raw_order: document.getElementById("full-raworder").value || null,
        preferences: readPrefs("full"),
      };
      const { ok, data } = await postJSON("/api/full_workflow", body);
      if (!ok) flashBanner("Full workflow failed: " + (data.error || ""), "err");
      hideEmpty("full-empty");
      renderWorkflow("full-output", data);
      updateProgress(data);
      storeLastRun(data);
      await refreshAudit();
    } finally { btn.disabled = false; }
  });

  // ===================================================================
  // Common Quick Starts — pre-fill realistic employee inputs only.
  // These never produce outputs. The user must still click Run.
  // ===================================================================

  // Helper: set a field's value AND dispatch a change event so the
  // validation listeners (which only fire on user interaction by default)
  // clear any prior `invalid` state and hide the error block.
  function setField(id, value) {
    const node = document.getElementById(id);
    if (!node) return;
    node.value = value;
    node.dispatchEvent(new Event("change", { bubbles: true }));
  }

  // Apply a complete quick-start preset by id.
  function applyQuickStart(key) {
    const presets = {
      "vanilla-latte": {
        store: "SD001", date: "2024-01-15", hour: "8",
        request: "I want an iced latte, something smooth and lightly sweet.",
        raworder: "grande iced vanilla latte with oat milk",
        prefs: {
          temp: "iced", sweet: "medium", milk: "oat milk",
          caffeine: "medium", coffee: "coffee", lowcal: "",
        },
        flash: "Pre-filled: Iced Vanilla Latte scenario. Click Run Full Workflow.",
      },
      "cold-brew": {
        store: "SD001", date: "2024-01-15", hour: "10",
        request: "I want something cold, coffee-forward, smooth, and a little sweet.",
        raworder: "grande vanilla sweet cream cold brew",
        prefs: {
          temp: "iced", sweet: "medium", milk: "",         // "no preference" → leave blank
          caffeine: "high", coffee: "coffee", lowcal: "",
        },
        flash: "Pre-filled: Vanilla Sweet Cream Cold Brew scenario. Click Run Full Workflow.",
      },
      "brown-sugar": {
        store: "SD001", date: "2024-01-15", hour: "8",
        request: "I want something iced, espresso-based, sweet, and made with oat milk.",
        raworder: "grande iced brown sugar oatmilk shaken espresso",
        prefs: {
          temp: "iced", sweet: "sweet", milk: "oat milk",
          caffeine: "high", coffee: "coffee", lowcal: "",
        },
        flash: "Pre-filled: Brown Sugar Oatmilk Shaken Espresso scenario. Click Run Full Workflow.",
      },
    };
    const p = presets[key];
    if (!p) return;
    // setGlobalStore syncs all form selects + topbar in one call
    if (window.setGlobalStore) window.setGlobalStore(p.store);
    else setField("full-store", p.store);
    setField("full-date", p.date);
    setField("full-hour", p.hour);
    setField("full-request", p.request);
    setField("full-raworder", p.raworder);
    setField("full-pref-temp", p.prefs.temp);
    setField("full-pref-sweet", p.prefs.sweet);
    setField("full-pref-milk", p.prefs.milk);
    setField("full-pref-caffeine", p.prefs.caffeine);
    setField("full-pref-coffee", p.prefs.coffee);
    setField("full-pref-lowcal", p.prefs.lowcal);
    flashBanner(p.flash, "ok");
  }

  document.querySelectorAll(".qs-card").forEach((btn) => {
    btn.addEventListener("click", () => applyQuickStart(btn.dataset.quickstart));
  });

  // ===================================================================
  // Audit log
  // ===================================================================
  async function refreshAudit(opts) {
    try {
      const res = await fetch("/api/audit_log");
      const data = await res.json();
      renderAudit(data.audit_log || [], window.__lastRun?.audit_log || []);
      if (opts && opts.open) toggleDrawer(true);
    } catch (e) { /* silent */ }
  }
  window.refreshAudit = refreshAudit;

  // Compact audit panels mirrored under Evidence Center and the Order Queue.
  // Shows the most recent entries newest-first; the full log lives in the drawer.
  function renderMiniAudit(all) {
    const recent = all.slice(-20).reverse();
    ["evi-audit-list", "queue-audit-list"].forEach((id) => {
      const ulx = document.getElementById(id);
      if (!ulx) return;
      ulx.innerHTML = "";
      if (!recent.length) {
        ulx.appendChild(el("li", { class: "muted small" }, ["No activity yet."]));
        return;
      }
      recent.forEach((e) => {
        const src = (e.source || "workflow").replace(/[^a-z_]/gi, "");
        const t = e.timestamp ? new Date(e.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "?";
        const li = el("li", { class: "mini-audit-item" }, [
          el("span", { class: "ts" }, [`${t} `]),
          el("span", { class: `src-${src}` }, [String(e.action || e.component || "?")]),
        ]);
        if (e.workflow_type) li.appendChild(document.createTextNode(` · ${e.workflow_type}`));
        if (e.status) li.appendChild(document.createTextNode(` · ${e.status}`));
        if (e.message) li.appendChild(el("div", { class: "mini-audit-msg" }, [e.message]));
        ulx.appendChild(li);
      });
    });
  }

  function renderAudit(uiLog, workflowLog) {
    const list = document.getElementById("audit-list");
    const count = document.getElementById("audit-count");
    list.innerHTML = "";
    const search = (document.getElementById("audit-search")?.value || "").toLowerCase();
    const all = [];
    workflowLog.forEach((e) => all.push({ source: "workflow", ...e }));
    uiLog.forEach((e) => all.push(e));
    count.textContent = `${all.length} entr${all.length === 1 ? "y" : "ies"}`;
    renderMiniAudit(all);
    if (!all.length) {
      list.appendChild(el("li", { class: "muted small" }, ["No audit entries yet."]));
      return;
    }
    let shown = 0;
    all.forEach((e) => {
      const text = `${e.timestamp || ""} ${e.source || ""} ${e.action || ""} ${e.component || ""} ${e.workflow_type || ""} ${e.status || ""} ${e.message || ""}`.toLowerCase();
      if (search && !text.includes(search)) return;
      shown++;
      const li = el("li");
      const src = (e.source || "workflow").replace(/[^a-z_]/gi, "");
      li.appendChild(el("span", { class: "ts" }, [`[${e.timestamp || "?"}] `]));
      li.appendChild(el("span", { class: `src-${src}` }, [`(${e.source || "workflow"}) `]));
      li.appendChild(el("strong", null, [e.action || e.component || "?"]));
      if (e.workflow_type) li.appendChild(document.createTextNode(` · ${e.workflow_type}`));
      if (e.status) li.appendChild(document.createTextNode(` · ${e.status}`));
      if (e.message) li.appendChild(document.createTextNode(` — ${e.message}`));
      list.appendChild(li);
    });
    if (search && shown === 0) {
      list.appendChild(el("li", { class: "muted small" }, [`No entries match "${search}".`]));
    }
  }

  document.getElementById("refresh-audit").addEventListener("click", () => refreshAudit());
  document.getElementById("clear-audit").addEventListener("click", async () => {
    await fetch("/api/audit_log", { method: "DELETE" });
    window.__reviewState = {};
    if (window.__lastRun) renderReviewQueue(window.__lastRun);
    refreshAudit();
  });
  document.getElementById("audit-search").addEventListener("input", () => {
    renderAudit([], []);  // re-render with no extra fetch
    refreshAudit();
  });

  // Initial audit fetch
  refreshAudit();

})();
