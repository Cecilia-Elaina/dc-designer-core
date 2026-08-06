const state = { sessions: [], current: null };
const stages = [
  ["scope", "范围与课题"], ["sources", "课程标准与来源"], ["goal", "评价需求与目的"],
  ["analysis", "教学分析与技能图"], ["learner_context", "学习者与环境"],
  ["objectives_assessment", "目标与评价"], ["strategy_materials", "策略与材料"], ["quality_export", "检查与导出"]
];

async function api(path, options = {}) {
  const response = await fetch(`/api/${path}`, { headers: { "Content-Type": "application/json" }, ...options });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || data.errors?.join("；") || "请求失败");
  return data;
}

function el(id) { return document.getElementById(id); }
function escapeHtml(value) { return String(value ?? "").replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[ch])); }

async function refreshProjects() {
  const data = await api("projects");
  state.sessions = data.sessions || [];
  const list = el("project-list");
  list.innerHTML = state.sessions.length ? state.sessions.map(item => `
    <button class="project-item ${state.current?.session_id === item.session_id ? "active" : ""}" data-session="${escapeHtml(item.session_id)}">
      <strong>${escapeHtml(item.project_id || "未命名项目")}</strong>
      <small>${escapeHtml(item.session_status || "草案")} · ${escapeHtml(item.current_stage_label || "")}</small>
    </button>`).join("") : `<p class="muted">还没有设计项目。</p>`;
  list.querySelectorAll("[data-session]").forEach(button => button.addEventListener("click", () => openSession(button.dataset.session)));
}

async function checkHealth() {
  try { const data = await api("health"); el("health").textContent = `本地工作区正常 · ${data.session_count} 个项目`; }
  catch (error) { el("health").textContent = `环境检查失败：${error.message}`; }
}

function renderProgress(session) {
  const current = session.current_stage;
  const completed = new Set(session.completed_stages || []);
  el("progress").innerHTML = stages.map(([id, label]) => `<div class="progress-step ${completed.has(id) ? "done" : ""} ${id === current ? "current" : ""}">${escapeHtml(label)}</div>`).join("");
}

function renderConfirmations(session) {
  const pending = (session.pending_confirmations || []).filter(item => item.status !== "confirmed");
  el("pending-count").textContent = pending.length;
  el("confirmations").innerHTML = pending.length ? pending.map(item => `
    <div class="confirmation"><p>${escapeHtml(item.question || item.confirmation_id)}</p>
      <button data-confirm="${escapeHtml(item.confirmation_id)}">确认这一项</button>
      <button class="defer" data-defer="${escapeHtml(item.confirmation_id)}">暂不确定</button></div>`).join("") : `<p class="muted">当前没有待确认事项。完成视觉检查和导出门禁后才可成为最终版。</p>`;
  el("confirmations").querySelectorAll("[data-confirm]").forEach(button => button.addEventListener("click", () => applyDecisions([{ confirmation_id: button.dataset.confirm, confirmed: true }])));
  el("confirmations").querySelectorAll("[data-defer]").forEach(button => button.addEventListener("click", () => applyDecisions([{ confirmation_id: button.dataset.defer, confirmed: false }])));
}

function renderExports(session) {
  const exports = session.export_result || session.last_result?.export_result || {};
  const entries = Object.entries(exports).filter(([key, value]) => typeof value === "string" && value);
  el("export-note").textContent = session.can_export_final ? "最终门禁已通过" : (session.final_blocking_reasons || []).slice(0, 2).join("；") || "当前为草案或待确认版本";
  el("exports").innerHTML = entries.length ? entries.map(([key, path]) => {
    const preview = /\.(md|txt|json|csv)$/i.test(path) ? `<button class="text-button" data-preview-path="${escapeHtml(path)}">预览</button>` : "";
    return `<div class="export-item"><a href="/api/file?path=${encodeURIComponent(path)}" target="_blank">${escapeHtml(key)}</a>${preview}<span>${escapeHtml(path)}</span></div>`;
  }).join("") : `<p class="muted">当前尚未生成可下载文件。</p>`;
  el("exports").querySelectorAll("[data-preview-path]").forEach(button => button.addEventListener("click", () => previewFile(button.dataset.previewPath)));
}

function renderSession(session) {
  state.current = session;
  el("empty-state").hidden = true;
  el("project-view").hidden = false;
  el("project-id").textContent = `${session.project_id || "未命名项目"} · v${session.project_version || 1}`;
  el("project-title").textContent = session.project_title || "教学系统设计项目";
  el("project-status").textContent = `${session.session_status || "草案"} · ${session.next_action || "继续确认当前阶段"}`;
  renderProgress(session); renderConfirmations(session); renderExports(session);
  el("decision-log").textContent = JSON.stringify(session.decision_log || [], null, 2);
  refreshProjects();
}

async function openSession(sessionId) {
  try { renderSession(await api(`sessions/${encodeURIComponent(sessionId)}`)); await loadSources(); }
  catch (error) { alert(error.message); }
}

async function applyDecisions(decisions) {
  if (!state.current) return;
  try { const result = await api(`sessions/${encodeURIComponent(state.current.session_id)}/decisions`, { method: "POST", body: JSON.stringify({ decisions }) }); renderSession(result.session); await loadSources(); }
  catch (error) { alert(error.message); }
}

async function loadSources() {
  try {
    const data = await api("sources");
    const sourceCards = (data.sources || []).slice(0, 12).map(source => {
      const isLocal = source.snapshot_id === "local-update";
      const action = isLocal ? `<button class="text-button" data-delete-source="${escapeHtml(source.source_id)}">删除本机来源</button>` : "";
      const clause = (source.clauses || [])[0] || {};
      return `<article class="source"><div class="source-title"><strong>${escapeHtml(source.title)}</strong>${action}</div><p>${escapeHtml(source.issuer)} · ${escapeHtml(source.version)} · ${escapeHtml(source.status)}</p><p>适用范围：${escapeHtml((source.stage || []).join("、"))}；证据状态：${escapeHtml(source.provenance?.verification_status || "待教师核对")}</p><p>条款：${escapeHtml(clause.clause_id || "未提供")}；定位：${escapeHtml(clause.page_number || clause.anchor || "待补充")}</p><p>${escapeHtml(clause.normalized_summary || clause.clause_text || "暂无条款摘要")}</p><a href="${escapeHtml(source.source_url)}" target="_blank" rel="noreferrer">查看官方链接</a></article>`;
    }).join("");
    const pending = (data.pending_updates || []).filter(item => item.status === "pending_review").map(item => `<article class="source pending"><strong>待审核更新：${escapeHtml(item.update_id)}</strong><p>${escapeHtml(item.url)} · SHA256 ${escapeHtml(item.sha256 || "未记录")}</p><button class="text-button" data-approve-update="${escapeHtml(item.update_id)}">填写元数据并审核</button></article>`).join("");
    const history = (data.source_history || []).slice(-8).map(item => `<article class="source history"><strong>历史版本：${escapeHtml(item.title || item.source_id)}</strong><p>${escapeHtml(item.version || "未提供")} · 已被替换：${escapeHtml(item.superseded_at || "未记录")}</p></article>`).join("");
    const historyHeading = history ? `<p class="muted source-history-heading">来源替换历史</p>` : "";
    el("sources").innerHTML = (sourceCards || pending || history) ? `${sourceCards}${pending}${historyHeading}${history}` : `<p class="muted">当前没有可用官方来源。</p>`;
    el("sources").querySelectorAll("[data-delete-source]").forEach(button => button.addEventListener("click", async () => {
      if (!confirm("删除这条本机来源记录？内置官方快照不会受影响。")) return;
      try { await api(`sources/${encodeURIComponent(button.dataset.deleteSource)}`, { method: "DELETE" }); await loadSources(); }
      catch (error) { alert(error.message); }
    }));
    el("sources").querySelectorAll("[data-approve-update]").forEach(button => button.addEventListener("click", () => {
      el("source-approve-form").elements.update_id.value = button.dataset.approveUpdate;
      el("source-approve-dialog").showModal();
    }));
  } catch (error) { el("sources").innerHTML = `<p class="muted">来源加载失败：${escapeHtml(error.message)}</p>`; }
}

async function loadKnowledge() {
  try {
    const data = await api("knowledge");
    el("knowledge").innerHTML = (data.matches || []).map(item => `<article class="source"><div class="source-title"><strong>${escapeHtml(item.title)}</strong><button class="text-button" data-delete-knowledge="${escapeHtml(item.document_id)}">删除</button></div><p>${escapeHtml(item.document_type)} · ${escapeHtml(item.file_name)}</p></article>`).join("") || `<p class="muted">没有已导入的教师资料。</p>`;
    el("knowledge").querySelectorAll("[data-delete-knowledge]").forEach(button => button.addEventListener("click", async () => {
      if (!confirm("删除这份本机教师资料？")) return;
      try { await api(`knowledge/${encodeURIComponent(button.dataset.deleteKnowledge)}`, { method: "DELETE" }); await loadKnowledge(); }
      catch (error) { alert(error.message); }
    }));
  } catch (error) { el("knowledge").innerHTML = `<p class="muted">资料加载失败：${escapeHtml(error.message)}</p>`; }
}

async function previewFile(path) {
  try { const response = await fetch(`/api/preview?path=${encodeURIComponent(path)}`); if (!response.ok) throw new Error("该文件不支持文本预览"); el("preview").textContent = await response.text(); el("preview-panel").hidden = false; }
  catch (error) { alert(error.message); }
}

async function showDoctor() {
  try { const report = await api("doctor"); const failures = report.checks.filter(item => item.status === "fail"); const warnings = report.checks.filter(item => item.status === "warning"); alert(`环境状态：${report.status}\n核心失败：${failures.length}\n可选提示：${warnings.length}\n\n${warnings.map(item => `${item.name}: ${item.error || item.detail || "需要注意"}`).join("\n")}`); }
  catch (error) { alert(error.message); }
}

async function deleteCurrentProject() {
  if (!state.current || !confirm("删除当前项目及其本机导出文件？此操作不可撤销。")) return;
  try {
    await api(`sessions/${encodeURIComponent(state.current.session_id)}`, { method: "DELETE" });
    state.current = null; el("project-view").hidden = true; el("empty-state").hidden = false;
    await refreshProjects(); await checkHealth();
  } catch (error) { alert(error.message); }
}

async function copyCurrentProject() {
  if (!state.current) return;
  try { const result = await api(`sessions/${encodeURIComponent(state.current.session_id)}/copy`, { method: "POST", body: "{}" }); renderSession(result.session); await loadSources(); }
  catch (error) { alert(error.message); }
}

async function compareCurrentProject() {
  if (!state.current || Number(state.current.project_version || 1) < 2) return alert("当前项目还没有两个可比较的版本。");
  try {
    const result = await api(`sessions/${encodeURIComponent(state.current.session_id)}/compare/1/${encodeURIComponent(state.current.project_version)}`);
    alert(`v1 到 v${result.to_version} 共变化 ${result.changed_section_count} 个设计模块。`);
  } catch (error) { alert(error.message); }
}

function showNewDialog() { el("new-dialog").showModal(); }

el("new-project").addEventListener("click", showNewDialog);
el("empty-new").addEventListener("click", showNewDialog);
el("refresh").addEventListener("click", () => state.current && openSession(state.current.session_id));
el("load-sources").addEventListener("click", loadSources);
el("load-knowledge").addEventListener("click", loadKnowledge);
el("knowledge-form").addEventListener("submit", async event => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const path = String(form.get("path") || "").trim();
  const topic = String(form.get("topic") || "").trim();
  try {
    const result = await api("knowledge", { method: "POST", body: JSON.stringify({ path, metadata: { topic } }) });
    await loadKnowledge();
    alert(result.ingested ? "资料已保存在本机个人知识库。" : "资料未导入，请查看提示。");
  } catch (error) { alert(error.message); }
});
el("doctor").addEventListener("click", showDoctor);
el("close-preview").addEventListener("click", () => { el("preview-panel").hidden = true; });
el("update-source").addEventListener("click", () => el("source-dialog").showModal());
el("delete-project").addEventListener("click", deleteCurrentProject);
el("copy-project").addEventListener("click", copyCurrentProject);
el("compare-project").addEventListener("click", compareCurrentProject);
el("apply-edit").addEventListener("click", () => {
  const field = el("field-path").value; let value = el("field-value").value.trim();
  if (!value) return alert("请填写需要修改的内容。");
  if (field === "class_profile") { try { value = JSON.parse(value); } catch { return alert("班级共性学情 JSON 格式不正确。"); } }
  applyDecisions([{ field_path: field, value }]);
});
el("new-form").addEventListener("submit", async event => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const classText = String(form.get("class_profile") || "").trim();
  const request = {
    education_scope: "k12_info_technology", subject: "信息科技", stage: form.get("stage"), grade_level: form.get("grade_level"),
    topic: form.get("topic"), mode: form.get("mode"), periods: form.get("periods"), equipment: form.get("equipment"),
    class_profile: classText ? { common_difficulties: [classText] } : {},
  };
  try { const result = await api("projects", { method: "POST", body: JSON.stringify(request) }); el("new-dialog").close(); renderSession(result.session); await loadSources(); await loadKnowledge(); }
  catch (error) { alert(error.message); }
});
el("source-form").addEventListener("submit", async event => {
  event.preventDefault();
  const url = String(new FormData(event.currentTarget).get("url") || "").trim();
  try { const result = await api("sources/update", { method: "POST", body: JSON.stringify({ url }) }); el("source-dialog").close(); await loadSources(); alert(result.status === "pending_review" ? "文件已进入待审核区。" : (result.reason || result.error || "处理完成")); }
  catch (error) { alert(error.message); }
});
el("source-approve-form").addEventListener("submit", async event => {
  event.preventDefault();
  const form = new FormData(event.currentTarget); let sourceRecord;
  try { sourceRecord = JSON.parse(String(form.get("source_record") || "")); } catch { return alert("来源记录 JSON 格式不正确。"); }
  try { const result = await api("sources/approve", { method: "POST", body: JSON.stringify({ update_id: form.get("update_id"), teacher_confirmed: true, source_record: sourceRecord }) }); el("source-approve-dialog").close(); await loadSources(); alert(result.status === "approved" ? "来源已启用并保存历史记录。" : (result.reason || "来源未启用")); }
  catch (error) { alert(error.message); }
});

checkHealth(); refreshProjects(); loadKnowledge();
