const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];

const state = {
  label: null,        // 当前说明书
  script: null,
  basket: [],         // [{id, name}]
  samples: [],
  busy: false,
};

const SECTION_DEFS = [
  ["indications", "适应症 / 治什么", ""],
  ["dosage", "用法用量", "primary"],
  ["contraindications", "禁忌（这些人不能吃）", "warn"],
  ["adverse_reactions", "可能出现的不舒服", ""],
  ["precautions", "注意事项", ""],
  ["interactions", "和其他药的相互影响", "warn"],
  ["special_populations", "老人 / 特殊人群", ""],
  ["storage", "怎么存放", ""],
];

/* ------------------------------------------------------------ 基础工具 */
function toast(msg, ms = 2200) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(t._t);
  t._t = setTimeout(() => t.classList.remove("show"), ms);
}

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || data.error || `请求失败 ${res.status}`);
  return data;
}

function setBusy(btn, busy, label) {
  if (!btn) return;
  if (busy) {
    btn._html = btn.innerHTML;
    btn.innerHTML = `<span class="loading"></span>${label || "处理中"}`;
    btn.disabled = true;
  } else {
    if (btn._html) btn.innerHTML = btn._html;
    btn.disabled = false;
  }
}

/* --------------------------------------------------------------- 标签页 */
$$(".tab").forEach((tab) => {
  tab.onclick = () => {
    $$(".tab").forEach((t) => t.classList.remove("active"));
    $$(".panel").forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    $("#panel-" + tab.dataset.tab).classList.add("active");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
});

$("#fontToggle").onclick = () => {
  document.body.classList.toggle("big");
  toast(document.body.classList.contains("big") ? "已切换大字号" : "已恢复标准字号");
};

/* --------------------------------------------------------------- 健康检查 */
async function health() {
  try {
    const h = await api("/api/health");
    const dot = $("#statusDot");
    dot.className = "dot " + (h.llm_configured ? "ok" : "bad");
    dot.title = h.llm_configured ? `模型就绪：${h.model}` : "未配置大模型 Key";
  } catch { $("#statusDot").className = "dot bad"; }
}

/* --------------------------------------------------------------- 示例列表 */
async function loadSamples() {
  state.samples = await api("/api/samples");
  $("#sampleChips").innerHTML = state.samples
    .map((s) => `<button class="chip" data-id="${s.id}">${s.title}<span style="color:#9bb0a9;font-size:12px"> · ${s.subtitle}</span></button>`)
    .join("");
  $$("#sampleChips .chip").forEach((c) => (c.onclick = () => openDemo(c.dataset.id)));
  $("#basketSamples").innerHTML = state.samples
    .map((s) => `<button class="chip" data-id="${s.id}">＋ ${s.title}</button>`)
    .join("");
  $$("#basketSamples .chip").forEach((c) => (c.onclick = () => addToBasket(c.dataset.id)));
}

async function openDemo(id) {
  try {
    const { label } = await api(`/api/demo/${id}`, { method: "POST" });
    renderLabel(label);
    toast("已载入示例说明书");
  } catch (e) { toast(e.message); }
}

/* --------------------------------------------------------------- 渲染说明书 */
function renderLabel(label) {
  state.label = label;
  state.script = null;
  $("#labelEmpty").classList.add("hidden");
  $("#labelBody").classList.remove("hidden");
  $("#playerCard").classList.add("hidden");

  $("#drugName").textContent = label.drug_name || "未识别出药名";
  $("#drugSpec").textContent = [label.spec, label.storage].filter(Boolean).join(" · ") || "说明书信息";
  const conf = Math.round((label.confidence || 0) * 100);
  $("#drugConf").textContent = conf ? `识别置信度 ${conf}%` : "识别完成";
  $("#drugConf").style.background = conf && conf < 80 ? "var(--amber-soft)" : "";
  $("#drugConf").style.color = conf && conf < 80 ? "var(--amber)" : "";

  const html = SECTION_DEFS.map(([key, title, cls]) => {
    let items = label[key];
    if (typeof items === "string") items = items ? [items] : [];
    if (!Array.isArray(items) || !items.length) return "";
    const lis = items.map((x) => `<li>${escapeHtml(x)}</li>`).join("");
    return `<div class="sec ${cls}">
      <div class="sec-head"><h3>${title}</h3><span class="count">${items.length} 条</span></div>
      <ul>${lis}</ul></div>`;
  }).join("");
  $("#labelSections").innerHTML = html ||
    `<div class="empty small">这张说明书没有识别出结构化内容，请换一张更清晰的图片</div>`;
  if (label._meta && label._meta.ms) {
    $("#drugConf").textContent += ` · ${(label._meta.ms / 1000).toFixed(1)}s`;
  }
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/* --------------------------------------------------------------- 上传解析 */
$("#uploader").onclick = () => $("#fileInput").click();
$("#fileInput").onchange = async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const fd = new FormData();
  fd.append("file", file);
  try {
    $("#uploader").querySelector(".up-title").textContent = "正在识别说明书……";
    const { label } = await api("/api/parse", { method: "POST", body: fd });
    renderLabel(label);
    toast("说明书识别完成");
  } catch (err) { toast(err.message, 3200); }
  finally {
    $("#uploader").querySelector(".up-title").textContent = "点击拍照 / 选择照片";
    e.target.value = "";
  }
};

$("#btnTextMode").onclick = () => {
  $("#textInput").classList.toggle("hidden");
  $("#btnParseText").classList.toggle("hidden");
};

$("#btnParseText").onclick = async () => {
  const text = $("#textInput").value.trim();
  if (!text) return toast("请先粘贴说明书文字");
  const btn = $("#btnParseText");
  setBusy(btn, true, "解析中");
  try {
    const fd = new FormData();
    fd.append("text", text);
    const { label } = await api("/api/parse", { method: "POST", body: fd });
    renderLabel(label);
    toast("解析完成");
  } catch (e) { toast(e.message, 3200); }
  finally { setBusy(btn, false); }
};

/* --------------------------------------------------------------- 语音播报 */
$("#btnExplain").onclick = async () => {
  if (!state.label) return toast("请先上传说明书");
  const btn = $("#btnExplain");
  setBusy(btn, true, "正在生成播报");
  try {
    const res = await api("/api/explain", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ label_id: state.label.id }),
    });
    state.script = res;
    renderScript(res);
    toast("播报已生成，点播放键收听");
  } catch (e) { toast(e.message, 3600); }
  finally { setBusy(btn, false); }
};

function renderScript(res) {
  $("#playerCard").classList.remove("hidden");
  const s = res.script;
  $("#playerMeta").textContent = `${s.chars} 字 · 约 ${s.est_seconds} 秒 · 语速已放慢`;
  $("#transcript").innerHTML = s.segments
    .map((seg) => `<div class="tseg"><div class="t">${escapeHtml(seg.title)}</div><div class="x">${escapeHtml(seg.text)}</div></div>`)
    .join("");
  $("#scanDisclaimer").textContent = res.disclaimer;
  const audio = $("#audio");
  audio.src = res.audio.url;
  audio.load();
  $("#progressBar").style.width = "0%";
  $("#timeLabel").textContent = "00:00 / 00:00";
}

const audio = $("#audio");
$("#playBtn").onclick = () => {
  if (!audio.src) return toast("请先生成播报");
  if (audio.paused) audio.play(); else audio.pause();
};
audio.onplay = () => ($("#playBtn").textContent = "❚❚");
audio.onpause = () => ($("#playBtn").textContent = "▶");
audio.onended = () => { $("#playBtn").textContent = "▶"; highlightSegment(-1); };
audio.ontimeupdate = () => {
  if (!audio.duration) return;
  const p = (audio.currentTime / audio.duration) * 100;
  $("#progressBar").style.width = p + "%";
  $("#timeLabel").textContent = `${fmt(audio.currentTime)} / ${fmt(audio.duration)}`;
  const segs = $$(".tseg");
  if (!segs.length) return;
  const idx = Math.min(segs.length - 1, Math.floor((audio.currentTime / audio.duration) * segs.length));
  highlightSegment(idx);
};
$("#rateSel").onchange = (e) => { audio.playbackRate = parseFloat(e.target.value); };
function highlightSegment(i) {
  $$(".tseg").forEach((el, k) => el.classList.toggle("active", k === i));
}
function fmt(t) {
  const m = Math.floor(t / 60), s = Math.floor(t % 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

/* --------------------------------------------------------------- 用药清单 */
$("#btnAddToList").onclick = () => {
  if (!state.label) return;
  if (state.basket.some((b) => b.id === state.label.id)) return toast("已经在清单里了");
  state.basket.push({ id: state.label.id, name: state.label.drug_name });
  renderBasket();
  toast("已加入多药检查清单");
};

async function addToBasket(sampleId) {
  const { label } = await api(`/api/demo/${sampleId}`, { method: "POST" });
  if (state.basket.some((b) => b.name === label.drug_name)) return toast("已经在清单里了");
  state.basket.push({ id: label.id, name: label.drug_name });
  renderBasket();
}

function renderBasket() {
  $("#basket").innerHTML = state.basket.length
    ? state.basket.map((b) => `<div class="med">💊 ${escapeHtml(b.name)}<button data-id="${b.id}">×</button></div>`).join("")
    : `<span class="hint">还没有添加药品，点下面的示例快速添加</span>`;
  $$("#basket .med button").forEach((btn) => {
    btn.onclick = () => {
      state.basket = state.basket.filter((b) => b.id !== btn.dataset.id);
      renderBasket();
    };
  });
}

/* --------------------------------------------------------------- 多药检查 */
$("#btnMix").onclick = async () => {
  if (state.basket.length < 2) return toast("至少添加两种药");
  const btn = $("#btnMix");
  setBusy(btn, true, "药师正在核对");
  try {
    const res = await api("/api/interactions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ label_ids: state.basket.map((b) => b.id) }),
    });
    renderMix(res);
  } catch (e) { toast(e.message, 3600); }
  finally { setBusy(btn, false); }
};

function renderMix(res) {
  $("#mixResult").classList.remove("hidden");
  const lv = res.overall_level || "未见风险";
  const pill = $("#mixLevel");
  pill.textContent = lv;
  pill.className = "level-pill level-" + lv;
  $("#mixFindings").innerHTML = (res.findings || [])
    .map((f) => `<div class="finding">
      <div class="row between"><h4>${escapeHtml(f.drug_a)} ＋ ${escapeHtml(f.drug_b)}</h4>
        <span class="level-pill level-${f.level}">${f.level}</span></div>
      <div class="row-line"><b>为什么会打架：</b>${escapeHtml(f.mechanism || "—")}</div>
      <div class="row-line"><b>可能后果：</b>${escapeHtml(f.consequence || "—")}</div>
      <div class="row-line"><b>该怎么做：</b>${escapeHtml(f.advice || "—")}</div>
      <div class="row-line" style="color:#88999;font-size:13px"><b>依据：</b>${escapeHtml(f.source || "说明书 / 知识库")}</div>
    </div>`).join("") || `<div class="empty small">未发现明确的相互作用</div>`;
  $("#mixSchedule").textContent = res.schedule_note || "";
  $("#mixSchedule").classList.toggle("hidden", !res.schedule_note);
  $("#mixDisclaimer").textContent = res.disclaimer || "";
  toast("检查完成");
}

/* --------------------------------------------------------------- 家属摘要 */
$("#btnFamily").onclick = async () => {
  if (!state.basket.length) return toast("请先在「多药检查」里添加药品");
  const btn = $("#btnFamily");
  setBusy(btn, true, "生成中");
  try {
    const res = await api("/api/family", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ label_ids: state.basket.map((b) => b.id) }),
    });
    state.family = res;
    renderFamily(res);
  } catch (e) { toast(e.message, 3600); }
  finally { setBusy(btn, false); }
};

function renderFamily(res) {
  const rows = (res.medications || [])
    .map((m) => `<tr><td><b>${escapeHtml(m.name)}</b></td><td>${escapeHtml(m.how)}</td><td>${escapeHtml(m.when)}</td></tr>`)
    .join("");
  const list = (arr, icon) => (arr || []).map((x) => `<li>${icon} ${escapeHtml(x)}</li>`).join("");
  $("#familyBody").innerHTML = `<div class="fam-card">
    <h3>${escapeHtml(res.title || "用药交接单")}</h3>
    <div class="fam-sub">生成时间 ${new Date().toLocaleString("zh-CN")} · 仅供参考</div>
    <table class="med-table"><thead><tr><th>药品</th><th>怎么吃</th><th>什么时候</th></tr></thead><tbody>${rows}</tbody></table>
    <div class="fam-sec"><h4>最需要盯的 3 件事</h4><ul>${list(res.watch_list, "•")}</ul></div>
    <div class="fam-sec"><h4>出现这些情况立刻送医</h4><ul>${list(res.emergency_signs, "⚠")}</ul></div>
    <div class="fam-sec"><h4>下次复诊要问医生</h4><ul>${list(res.ask_doctor, "?")}</ul></div>
    <p class="disclaimer">${escapeHtml(res.disclaimer || "")}</p>
  </div>`;
}

$("#btnCopyFamily").onclick = () => {
  if (!state.family) return toast("请先生成交接单");
  const r = state.family;
  const text = [r.title, ...(r.medications || []).map((m) => `${m.name}｜${m.how}｜${m.when}`),
    "需要盯：" + (r.watch_list || []).join("；"),
    "紧急信号：" + (r.emergency_signs || []).join("；")].join("\n");
  navigator.clipboard?.writeText(text).then(() => toast("已复制，可以发给家人了"));
};

/* --------------------------------------------------------------- 问答 */
const QUICK_Q = [
  "这个药饭前吃还是饭后吃？",
  "一次吃几片？一天吃几次？",
  "吃了会有什么不舒服？",
  "我还能喝酒吗？",
  "漏吃了一次怎么办？",
  "这个药能治好吗？",
];
$("#qChips").innerHTML = QUICK_Q.map((q) => `<button class="chip">${q}</button>`).join("");
$$("#qChips .chip").forEach((c) => (c.onclick = () => { $("#askInput").value = c.textContent; submitAsk(); }));

$("#btnAsk").onclick = submitAsk;
$("#askInput").onkeydown = (e) => { if (e.key === "Enter") submitAsk(); };

async function submitAsk() {
  const q = $("#askInput").value.trim();
  if (!q) return;
  if (!state.label) return toast("请先在「拍照解读」里上传一张说明书");
  const chat = $("#chat");
  chat.insertAdjacentHTML("beforeend", `<div class="msg user">${escapeHtml(q)}</div>`);
  $("#askInput").value = "";
  const thinking = document.createElement("div");
  thinking.className = "msg bot";
  thinking.innerHTML = `<span class="loading" style="border-color:#cfe3dc;border-top-color:#0f7a68"></span>正在查说明书……`;
  chat.appendChild(thinking);
  chat.scrollTop = chat.scrollHeight;

  const agentMode = $("#agentMode").checked;
  try {
    const res = agentMode
      ? await api("/api/agent", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ label_id: state.label.id, question: q }) })
      : await api("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ label_id: state.label.id, question: q }) });

    thinking.innerHTML = renderAnswer(res);
    if (res.trace) renderTrace(res.trace);
    else if (res.evidence) renderTraceFromEvidence(res);
  } catch (e) {
    thinking.innerHTML = `<span style="color:#c8392f">出错了：${escapeHtml(e.message)}</span>`;
  }
  chat.scrollTop = chat.scrollHeight;
}

function renderAnswer(res) {
  const text = (res.answer || "").trim();
  if (text.length < 4) {
    return `<span style="color:#c8392f">这次没生成出完整回答，请再问一次。</span>`;
  }
  const cites = (res.citations || [])
    .map((c) => `<span class="cite" title="${escapeHtml(c.text)}">[${c.id}] ${escapeHtml(c.text.slice(0, 18))}…</span>`)
    .join("");
  const doc = res.need_doctor ? `<div class="need-doctor">建议就医 / 咨询药师后再决定</div>` : "";
  const guarded = res.guard && res.guard.pass === false
    ? `<div class="need-doctor">安全护栏已介入：部分内容已改为保守表述</div>` : "";
  return `${mdToHtml(res.answer)}${doc}${guarded}${cites ? `<div class="cites">${cites}</div>` : ""}`;
}

// 极简 Markdown：只处理 **加粗** 和换行，避免模型输出的星号直接露出来
function mdToHtml(text) {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, "<b>$1</b>")
    .replace(/\n/g, "<br>");
}

function renderTrace(trace) {
  const box = $("#traceBox");
  box.innerHTML = trace.map((t) => {
    if (t.type === "tool") {
      return `<div class="step"><div class="hd">🔧 ${escapeHtml(t.tool)} <span class="lat">${t.ms}ms</span></div>
        <pre>入参 ${escapeHtml(JSON.stringify(t.args, null, 0))}\n返回 ${escapeHtml(JSON.stringify(t.result, null, 0)).slice(0, 320)}</pre></div>`;
    }
    if (t.type === "final") {
      return `<div class="step final"><div class="hd">✅ 生成回答</div><pre>${escapeHtml(t.content || "").slice(0, 300)}</pre></div>`;
    }
    return `<div class="step"><div class="hd">ℹ️ ${escapeHtml(t.type)}</div></div>`;
  }).join("");
  box.scrollTop = 0;
}

function renderTraceFromEvidence(res) {
  const ev = (res.evidence || [])
    .map((e) => `<pre>[${e.id}] ${escapeHtml(e.text)}</pre>`).join("");
  const g = res.guard || {};
  const rule = g.rule ? `数字核对：${(g.rule.unsupported_numbers || []).length ? "发现存疑 " + g.rule.unsupported_numbers.join(",") : "全部通过"}\n引用核对：${(g.rule.invalid_citations || []).length ? "越界编号" : "通过"}` : "";
  $("#traceBox").innerHTML = `<div class="step"><div class="hd">🔍 检索到的证据</div>${ev}</div>
    <div class="step final"><div class="hd">🛡 护栏复核</div><pre>${escapeHtml(rule || "已通过")}</pre></div>`;
}

/* --------------------------------------------------------------- 启动 */
(async function init() {
  health();
  await loadSamples();
  renderBasket();
  // 预置两种药，方便直接演示
  try {
    for (const id of ["lipitor", "klaricid"]) {
      const { label } = await api(`/api/demo/${id}`, { method: "POST" });
      if (!state.basket.some((b) => b.name === label.drug_name)) {
        state.basket.push({ id: label.id, name: label.drug_name });
      }
    }
    renderBasket();
  } catch (e) { /* 模型未配置时忽略 */ }
})();
