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
    };
    Object.keys(map).forEach((k) => {
      const inp = document.getElementById(`${idPrefix}-pref-${k}`);
      if (!inp || !inp.value.trim()) return;
      let v = inp.value.trim();
      if (k === "lowcal") v = /^(true|1|yes)$/i.test(v);
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
  function faceValidityCard(fv) {
    if (!fv) return el("div", { class: "card muted" }, ["No face_validity attached."]);
    const cls = fv.status || "not_applicable";
    const card = el("div", { class: `fv-card ${cls}` });
    card.appendChild(el("h3", null, [
      "🎯 Face Validity ",
      el("span", { class: `pill ${fvBadgeClass(cls)}` }, [fv.status || "—"]),
    ]));
    card.appendChild(el("div", { class: "fv-row" }, [
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
      card.appendChild(row);
    }
    if (fv.supporting_reasons?.length) {
      card.appendChild(el("h4", null, ["Supporting reasons"]));
      const ul = el("ul", { class: "fv-list" });
      fv.supporting_reasons.forEach((r) => ul.appendChild(el("li", null, [r])));
      card.appendChild(ul);
    }
    if (fv.concerns?.length) {
      card.appendChild(el("h4", null, ["Concerns"]));
      const ul = el("ul", { class: "fv-list" });
      fv.concerns.forEach((r) => ul.appendChild(el("li", null, [r])));
      card.appendChild(ul);
    }
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
    const q = document.getElementById("sub-quality");
    q.innerHTML = "";
    q.appendChild(faceValidityCard(run.face_validity));
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

  function managerBody(fo) {
    const body = el("div");
    const rs = fo.readiness_summary || {};
    body.appendChild(el("div", { class: "muted small" }, [
      `overall=${rs.overall_status || "—"} · demand=${rs.demand_risk || "—"} / ${rs.demand_level || "—"} · staffing_gap=${rs.staffing_gap ?? "—"} · inv_unavailable=${rs.inventory_unavailable_count ?? "—"} · inv_low=${rs.inventory_low_count ?? "—"} · promos=${rs.active_promotions_count ?? "—"} · forecast=${rs.forecast_orders ?? "—"}`,
    ]));
    const actions = fo.recommended_actions || [];
    if (actions.length) {
      body.appendChild(el("h4", null, ["Recommended manager actions"]));
      const ul = el("ul", null);
      actions.forEach((a) => ul.appendChild(el("li", null, [a])));
      body.appendChild(ul);
    }
    const bg = fo.barista_guidance || {};
    if (Object.keys(bg).length) {
      body.appendChild(el("h4", null, ["Barista guidance"]));
      Object.entries(bg).forEach(([k, v]) => body.appendChild(el("div", { class: "muted small" }, [el("strong", null, [`${k}: `]), Array.isArray(v) ? v.join(", ") : String(v)])));
    }
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
    root.appendChild(faceValidityCard(run.face_validity));

    const wf = run.workflow_type;
    const fo = run.final_output || {};

    if (wf === "manager_readiness") {
      root.appendChild(outCard("👤 Manager Readiness", managerBody(fo), true));
    } else if (wf === "barista_recommendation") {
      root.appendChild(outCard("🧋 Recommendation", recBody(fo), true));
    } else if (wf === "order_builder") {
      root.appendChild(outCard("📝 Order Builder", orderBody(fo), true));
    } else if (wf === "full_workflow") {
      if (fo.manager_readiness) root.appendChild(outCard("👤 Manager Readiness", managerBody(fo.manager_readiness), true));
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

  document.getElementById("run-barista").addEventListener("click", async (e) => {
    if (!validateFields(["bar-store", "bar-date", "bar-hour", "bar-request"])) return;
    const btn = e.currentTarget; btn.disabled = true;
    try {
      const body = {
        store_id: document.getElementById("bar-store").value,
        date: document.getElementById("bar-date").value || "2024-01-15",
        hour: Number(document.getElementById("bar-hour").value),
        customer_request: document.getElementById("bar-request").value || "",
        preferences: readPrefs("bar"),
      };
      const { ok, data } = await postJSON("/api/barista_recommendation", body);
      if (!ok) flashBanner("Recommendation failed: " + (data.error || ""), "err");
      hideEmpty("barista-empty");
      renderWorkflow("barista-output", data);
      storeLastRun(data);
      await refreshAudit();
    } finally { btn.disabled = false; }
  });

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
    if (!validateFields(["full-store", "full-date", "full-hour", "full-request"])) return;
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
    setField("full-store", p.store);
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

  function renderAudit(uiLog, workflowLog) {
    const list = document.getElementById("audit-list");
    const count = document.getElementById("audit-count");
    list.innerHTML = "";
    const search = (document.getElementById("audit-search")?.value || "").toLowerCase();
    const all = [];
    workflowLog.forEach((e) => all.push({ source: "workflow", ...e }));
    uiLog.forEach((e) => all.push(e));
    count.textContent = `${all.length} entr${all.length === 1 ? "y" : "ies"}`;
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
