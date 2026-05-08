const stageMeta = [
  { key: "initiated", title: "需求发起", note: "乘客提出目的地与天数。" },
  { key: "confirming_info", title: "信息确认", note: "确认出发地、时间、预算与偏好。" },
  { key: "plan_generated", title: "方案生成", note: "展示结构化旅行方案。" },
  { key: "revising_plan", title: "方案调整", note: "根据语音意见局部重排。" },
  { key: "plan_confirmed", title: "方案确认", note: "锁定当前版本。" },
  { key: "shared", title: "保存分享", note: "保存并发送到乘客手机。" },
];

const state = {
  sessionId: null,
  response: null,
  scenes: [],
};

const elements = {
  frameStrip: document.querySelector("#frameStrip"),
  sessionBadge: document.querySelector("#sessionBadge"),
  assistantState: document.querySelector("#assistantState"),
  assistantMessage: document.querySelector("#assistantMessage"),
  stageLabel: document.querySelector("#stageLabel"),
  collectedInfo: document.querySelector("#collectedInfo"),
  missingInfo: document.querySelector("#missingInfo"),
  actionPanel: document.querySelector("#actionPanel"),
  planTitle: document.querySelector("#planTitle"),
  planSummary: document.querySelector("#planSummary"),
  budgetChip: document.querySelector("#budgetChip"),
  planTimeline: document.querySelector("#planTimeline"),
  planTips: document.querySelector("#planTips"),
  conversationList: document.querySelector("#conversationList"),
  userInput: document.querySelector("#userInput"),
  sendButton: document.querySelector("#sendButton"),
  confirmButton: document.querySelector("#confirmButton"),
  shareButton: document.querySelector("#shareButton"),
  restartButton: document.querySelector("#restartButton"),
  sceneList: document.querySelector("#sceneList"),
};

function currentStageMeta(stageKey) {
  return stageMeta.find((item) => item.key === stageKey) || stageMeta[0];
}

function createTag(label, value) {
  const tag = document.createElement("div");
  tag.className = "tag";
  const strong = document.createElement("strong");
  strong.textContent = `${label}：`;
  const span = document.createElement("span");
  span.textContent = value;
  tag.append(strong, span);
  return tag;
}

function createButton(action) {
  const button = document.createElement("button");
  button.className = `action-button ${action.kind === "confirm" || action.kind === "share" ? "highlight" : ""}`;
  button.textContent = action.label;
  button.addEventListener("click", () => handleAction(action));
  return button;
}

function renderFrameStrip(stageKey) {
  elements.frameStrip.innerHTML = "";
  stageMeta.forEach((item) => {
    const node = document.createElement("div");
    node.className = `frame-pill ${item.key === stageKey ? "active" : ""}`;
    const title = document.createElement("span");
    title.className = "frame-title";
    title.textContent = item.title;
    const note = document.createElement("span");
    note.className = "frame-note";
    note.textContent = item.note;
    node.append(title, note);
    elements.frameStrip.append(node);
  });
}

function renderCollectedInfo(collectedInfo) {
  elements.collectedInfo.innerHTML = "";
  const entries = Object.entries(collectedInfo || {});
  if (!entries.length) {
    elements.collectedInfo.append(createTag("状态", "还没有确认任何信息"));
    return;
  }
  entries.forEach(([label, value]) => {
    elements.collectedInfo.append(createTag(label, value));
  });
}

function renderMissingInfo(missingInfo) {
  elements.missingInfo.innerHTML = "";
  if (!missingInfo || !missingInfo.length) {
    elements.missingInfo.append(createTag("状态", "已补齐关键槽位"));
    return;
  }
  missingInfo.forEach((label) => {
    elements.missingInfo.append(createTag("待补充", label));
  });
}

function renderActions(actions) {
  elements.actionPanel.innerHTML = "";
  (actions || []).forEach((action) => {
    elements.actionPanel.append(createButton(action));
  });
}

function renderPlan(plan, stageKey) {
  if (!plan) {
    elements.planTitle.textContent = "等待发起需求";
    elements.planSummary.textContent = "告诉我你想去哪里、玩几天，我会继续追问出发地、时间和预算。";
    elements.budgetChip.textContent = currentStageMeta(stageKey).title;
    elements.planTimeline.className = "timeline empty-state";
    elements.planTimeline.textContent = "行程生成后，会在这里展示每日安排、转场方式和预算分布。";
    elements.planTips.innerHTML = "";
    return;
  }

  elements.planTitle.textContent = plan.title;
  elements.planSummary.textContent = plan.summary;
  elements.budgetChip.textContent = `预算 ${plan.total_estimated_cost} 元`;
  elements.planTimeline.className = "timeline";
  elements.planTimeline.innerHTML = "";
  plan.days.forEach((item) => {
    const card = document.createElement("article");
    card.className = "timeline-card";

    const left = document.createElement("div");
    const day = document.createElement("div");
    day.className = "timeline-day";
    day.textContent = `DAY ${item.day}`;
    const city = document.createElement("p");
    city.className = "timeline-city";
    city.textContent = item.city;
    left.append(day, city);

    const right = document.createElement("div");
    const theme = document.createElement("p");
    theme.textContent = item.theme;
    const meta = document.createElement("p");
    meta.className = "timeline-meta";
    meta.textContent = `${item.transport} | ${item.hotel_level} | 约 ${item.estimated_cost} 元`;
    const highlights = document.createElement("div");
    highlights.className = "highlights";
    item.highlights.forEach((highlight) => {
      const pill = document.createElement("span");
      pill.className = "highlight-pill";
      pill.textContent = highlight;
      highlights.append(pill);
    });
    right.append(theme, meta, highlights);

    card.append(left, right);
    elements.planTimeline.append(card);
  });

  elements.planTips.innerHTML = "";
  plan.tips.forEach((tip) => {
    const item = document.createElement("div");
    item.className = "tag";
    item.textContent = tip;
    elements.planTips.append(item);
  });
}

function renderConversation(history) {
  elements.conversationList.innerHTML = "";
  (history || []).forEach((turn) => {
    const bubble = document.createElement("div");
    bubble.className = `bubble ${turn.role}`;
    bubble.textContent = turn.text;
    elements.conversationList.append(bubble);
  });
}

function renderScenes() {
  elements.sceneList.innerHTML = "";
  state.scenes.forEach((scene) => {
    const button = document.createElement("button");
    button.className = "scene-button";
    const title = document.createElement("strong");
    title.textContent = scene.title;
    const utterance = document.createElement("span");
    utterance.textContent = scene.utterance;
    const note = document.createElement("span");
    note.textContent = scene.note;
    button.append(title, utterance, note);
    button.addEventListener("click", () => sendMessage(scene.utterance));
    elements.sceneList.append(button);
  });
}

function renderResponse(response) {
  state.response = response;
  state.sessionId = response.session_id;

  const meta = currentStageMeta(response.stage);
  elements.sessionBadge.textContent = `会话 ${response.session_id}`;
  elements.assistantMessage.textContent = response.message;
  elements.stageLabel.textContent = meta.title;
  elements.assistantState.textContent = {
    initiated: "正在聆听",
    confirming_info: "持续确认",
    plan_generated: "规划完成",
    revising_plan: "快速微调",
    plan_confirmed: "方案确认",
    shared: "已发手机",
  }[response.stage];

  renderFrameStrip(response.stage);
  renderCollectedInfo(response.collected_info);
  renderMissingInfo(response.missing_info);
  renderActions(response.actions);
  renderPlan(response.plan, response.stage);
  renderConversation(response.history);

  const hasPlan = Boolean(response.plan);
  elements.confirmButton.disabled = !hasPlan;
  elements.shareButton.disabled = !hasPlan;
}

async function request(path, payload) {
  const response = await fetch(path, {
    method: payload ? "POST" : "GET",
    headers: payload ? { "Content-Type": "application/json" } : undefined,
    body: payload ? JSON.stringify(payload) : undefined,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "请求失败" }));
    throw new Error(body.detail || "请求失败");
  }
  return response.json();
}

async function startSession() {
  const data = await request("/api/session/start", {});
  renderResponse(data);
}

async function loadScenes() {
  state.scenes = await request("/api/mock/scenes");
  renderScenes();
}

async function sendMessage(text) {
  const value = text.trim();
  if (!value || !state.sessionId) {
    return;
  }
  const hasPlan = Boolean(state.response?.plan);
  const useRevisionEndpoint =
    hasPlan &&
    ["plan_generated", "revising_plan", "plan_confirmed"].includes(state.response?.stage) &&
    !/确认|保存|分享|手机/.test(value);

  const path = useRevisionEndpoint ? "/api/plan/revise" : "/api/session/message";
  const payload = useRevisionEndpoint
    ? { session_id: state.sessionId, user_feedback: value }
    : { session_id: state.sessionId, text: value };

  const data = await request(path, payload);
  renderResponse(data);
  elements.userInput.value = "";
}

async function confirmPlan() {
  if (!state.sessionId) {
    return;
  }
  const data = await request("/api/plan/confirm", { session_id: state.sessionId });
  renderResponse(data);
}

async function sharePlan() {
  if (!state.sessionId) {
    return;
  }
  const data = await request("/api/plan/share", { session_id: state.sessionId });
  renderResponse(data);
}

async function handleAction(action) {
  if (action.kind === "confirm") {
    await confirmPlan();
    return;
  }
  if (action.kind === "share") {
    await sharePlan();
    return;
  }
  if (action.kind === "restart") {
    await startSession();
    return;
  }
  await sendMessage(action.value);
}

function bindEvents() {
  elements.sendButton.addEventListener("click", () => sendMessage(elements.userInput.value));
  elements.confirmButton.addEventListener("click", confirmPlan);
  elements.shareButton.addEventListener("click", sharePlan);
  elements.restartButton.addEventListener("click", startSession);
  elements.userInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      sendMessage(elements.userInput.value);
    }
  });
}

async function bootstrap() {
  bindEvents();
  try {
    await loadScenes();
    await startSession();
  } catch (error) {
    elements.assistantMessage.textContent = error.message;
  }
}

bootstrap();

