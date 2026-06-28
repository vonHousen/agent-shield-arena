const RUNS_POLL_INTERVAL_MS = 5000;
const ALL_FILTER = "all";

const state = {
  events: 0,
  currentScenario: null,
  currentRoundFilter: null,
  currentRoundNumber: null,
  activeScenarioKey: null,
  scenarioEvents: { [ALL_FILTER]: [] },
  scenarioEmptyPlaceholder: null,

  rounds: [],
  roundVerdicts: {},
  scenarios: 0,
  verdicts: 0,
  successfulVerdicts: 0,
  defenderDecisions: 0,
  defenderBlocks: 0,
  scenarioMetadata: {},
  scenarioMetrics: {
    [ALL_FILTER]: { messages: 0, toolCalls: 0, toolResults: 0 },
  },

  reflections: [],
  briefings: {},

  selectedRun: "latest",
  socket: null,
};

const elements = {
  statusBadge: document.querySelector("#statusBadge"),
  headerSummary: document.querySelector("#headerSummary"),
  conversation: document.querySelector("#conversation"),
  emptyState: document.querySelector("#emptyState"),
  scrollButton: document.querySelector("#scrollButton"),
  roundSelector: document.querySelector("#roundSelector"),
  scenarioTabs: document.querySelector("#scenarioTabs"),
  roundMetric: document.querySelector("#roundMetric"),
  scenarioMetric: document.querySelector("#scenarioMetric"),
  messageMetric: document.querySelector("#messageMetric"),
  toolCallMetric: document.querySelector("#toolCallMetric"),
  successRateMetric: document.querySelector("#successRateMetric"),
  blockMetric: document.querySelector("#blockMetric"),
  blockRateMetric: document.querySelector("#blockRateMetric"),
  verdictCard: document.querySelector("#verdictCard"),
  runSelector: document.querySelector("#runSelector"),
  roundComparisonCard: document.querySelector("#roundComparisonCard"),
  roundComparison: document.querySelector("#roundComparison"),
  adaptationCard: document.querySelector("#adaptationCard"),
  adaptationContent: document.querySelector("#adaptationContent"),
};

elements.scrollButton.addEventListener("click", () => {
  scrollConversationToBottom();
});

elements.roundSelector.addEventListener("click", (e) => {
  const button = e.target.closest(".round-button");
  if (button) {
    switchRound(button.dataset.round);
  }
});

elements.scenarioTabs.addEventListener("click", (e) => {
  const tab = e.target.closest(".scenario-tab");
  if (tab && !tab.classList.contains("hidden")) {
    switchTab(tab.dataset.scenario);
  }
});

elements.runSelector.addEventListener("change", () => {
  state.selectedRun = elements.runSelector.value;
  connectWebSocket();
});

fetchRuns();
connectWebSocket();
setInterval(fetchRuns, RUNS_POLL_INTERVAL_MS);

function connectWebSocket() {
  if (state.socket) {
    state.socket.close();
    state.socket = null;
  }

  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const runParam = encodeURIComponent(state.selectedRun);
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws?run=${runParam}`);
  state.socket = socket;

  socket.addEventListener("open", () => {
    resetState();
    setStatus("Idle", "idle");
  });

  socket.addEventListener("message", (message) => {
    const event = JSON.parse(message.data);
    if (event.type === "reset") {
      resetState();
      return;
    }
    renderEvent(event);
  });

  socket.addEventListener("close", () => {
    if (state.socket === socket) {
      setStatus("Idle", "idle");
      window.setTimeout(connectWebSocket, 1500);
    }
  });

  socket.addEventListener("error", () => {
    socket.close();
  });
}

async function fetchRuns() {
  try {
    const response = await fetch("/api/runs");
    const runs = await response.json();
    populateRunSelector(runs);
  } catch {
    /* network hiccup - retry on next interval */
  }
}

function populateRunSelector(runs) {
  const previous = state.selectedRun;

  while (elements.runSelector.options.length > 1) {
    elements.runSelector.remove(1);
  }

  for (const run of runs) {
    const option = document.createElement("option");
    option.value = run.id;
    option.textContent = formatRunLabel(run.timestamp);
    elements.runSelector.append(option);
  }

  elements.runSelector.value = previous;
  if (elements.runSelector.selectedIndex === -1) {
    elements.runSelector.value = "latest";
    state.selectedRun = "latest";
  }
}

function formatRunLabel(isoTimestamp) {
  const date = new Date(isoTimestamp);
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}

function renderEvent(event) {
  removeEmptyState();
  state.events += 1;

  event.roundNumber = state.currentRoundNumber;

  if (event.event_type === "run_started") {
    setStatus("Running", "running");
    return;
  }

  if (event.event_type === "run_completed") {
    setStatus("Completed", "completed");
    return;
  }

  if (event.event_type === "round_started") {
    handleRoundStarted(event.payload);
    updateMetrics();
    updateHeaderSummary();
    return;
  }

  if (event.event_type === "scenario_started") {
    handleScenarioStarted(event.payload);
    updateMetrics();
    updateHeaderSummary();
    return;
  }

  if (event.event_type === "attack_briefing") {
    handleAttackBriefing(event.payload);
    return;
  }

  if (event.event_type === "attack_reflection") {
    handleAttackReflection(event.payload);
    return;
  }

  storeEvent(event);
  handleConversationEvent(event);
  updateMetrics();
  updateHeaderSummary();
}

function handleRoundStarted(payload) {
  state.currentRoundNumber = payload.round_number;

  if (!state.rounds.includes(payload.round_number)) {
    state.rounds.push(payload.round_number);
    state.roundVerdicts[payload.round_number] = { pass: 0, fail: 0, total: payload.strategy_count };
    addRoundButton(payload.round_number);

    if (state.rounds.length === 1) {
      switchRound(String(payload.round_number));
    }
  }
}

function addRoundButton(roundNumber) {
  const button = document.createElement("button");
  button.className = "round-button";
  button.type = "button";
  button.dataset.round = String(roundNumber);

  const dot = document.createElement("span");
  dot.className = "round-dot round-dot-running";

  const label = document.createElement("span");
  label.className = "round-label";
  label.textContent = `Round ${roundNumber}`;

  button.append(dot, label);
  elements.roundSelector.append(button);
}

function updateRoundButtonLabel(roundNumber) {
  const button = elements.roundSelector.querySelector(`[data-round="${roundNumber}"]`);
  if (!button) {
    return;
  }

  const rv = state.roundVerdicts[roundNumber];
  const evaluated = rv.pass + rv.fail;

  const label = button.querySelector(".round-label");
  if (label) {
    label.textContent = `Round ${roundNumber} (${rv.fail}/${evaluated} defended)`;
  }

  const dot = button.querySelector(".round-dot");
  if (dot) {
    dot.className = "round-dot";
    if (evaluated >= rv.total) {
      dot.classList.add(rv.pass === 0 ? "round-dot-defended" : "round-dot-breached");
    } else {
      dot.classList.add("round-dot-running");
    }
  }
}

function updateRoundComparison() {
  const container = elements.roundComparison;
  container.innerHTML = "";

  const hasVerdicts = state.rounds.some((r) => {
    const rv = state.roundVerdicts[r];
    return rv && rv.pass + rv.fail > 0;
  });

  if (!hasVerdicts) {
    elements.roundComparisonCard.classList.add("hidden");
    return;
  }

  elements.roundComparisonCard.classList.remove("hidden");

  for (const roundNumber of state.rounds) {
    const rv = state.roundVerdicts[roundNumber];
    if (!rv) {
      continue;
    }

    const evaluated = rv.pass + rv.fail;
    if (evaluated === 0) {
      continue;
    }

    const defendedPercent = Math.round((rv.fail / evaluated) * 100);

    const row = document.createElement("div");
    row.className = "comparison-row";

    const labelEl = document.createElement("span");
    labelEl.className = "comparison-label";
    labelEl.textContent = `Round ${roundNumber}`;

    const barTrack = document.createElement("div");
    barTrack.className = "comparison-track";

    const barFill = document.createElement("div");
    barFill.className = "comparison-bar";
    barFill.style.width = `${defendedPercent}%`;

    if (evaluated < rv.total) {
      barFill.classList.add("comparison-bar-running");
    }

    barTrack.append(barFill);

    const countEl = document.createElement("span");
    countEl.className = "comparison-count";
    countEl.textContent = `${rv.fail}/${evaluated} defended`;

    row.append(labelEl, barTrack, countEl);
    container.append(row);
  }
}

function handleScenarioStarted(payload) {
  const roundNumber = state.currentRoundNumber;
  const scenarioKey = buildScenarioKey(roundNumber, payload.scenario_name);

  state.activeScenarioKey = scenarioKey;
  state.scenarios += 1;
  state.scenarioEvents[scenarioKey] = [];
  state.scenarioMetrics[scenarioKey] = { messages: 0, toolCalls: 0, toolResults: 0 };
  state.scenarioMetadata[scenarioKey] = {
    key: scenarioKey,
    name: payload.scenario_name,
    roundNumber,
    verdict: null,
  };

  const tab = document.createElement("button");
  tab.className = "scenario-tab";
  tab.type = "button";
  tab.dataset.scenario = scenarioKey;
  tab.dataset.round = roundNumber === null ? "" : String(roundNumber);

  const dot = document.createElement("span");
  dot.className = "round-dot round-dot-running";

  const label = document.createElement("span");
  label.textContent = humanizeName(payload.scenario_name);
  tab.append(dot, label);
  elements.scenarioTabs.append(tab);

  updateScenarioTabVisibility();
  switchTab(scenarioKey);
}

function storeEvent(event) {
  state.scenarioEvents[ALL_FILTER].push(event);
  if (state.activeScenarioKey) {
    state.scenarioEvents[state.activeScenarioKey].push(event);
  }
}

function handleConversationEvent(event) {
  if (event.event_type === "attacker_reasoning") {
    renderIfVisible(event, appendAttackerReasoning);
    return;
  }

  if (event.event_type === "conversation_turn") {
    incrementMetric("messages");
    renderIfVisible(event, appendConversationTurn);
    return;
  }

  if (event.event_type === "tool_call") {
    incrementMetric("toolCalls");
    renderIfVisible(event, appendToolCall);
    return;
  }

  if (event.event_type === "tool_result") {
    incrementMetric("toolResults");
    renderIfVisible(event, appendToolResult);
    return;
  }

  if (event.event_type === "defender_decision") {
    handleDefenderDecision(event);
    return;
  }

  if (event.event_type === "evaluation_verdict") {
    handleEvaluationVerdict(event);
    return;
  }

  if (event.event_type === "content_filter") {
    renderIfVisible(event, appendContentFilter);
  }
}

function handleDefenderDecision(event) {
  state.defenderDecisions += 1;
  if (event.payload.decision === "BLOCK") {
    state.defenderBlocks += 1;
  }

  renderIfVisible(event, appendDefenderDecision);
}

function handleEvaluationVerdict(event) {
  state.verdicts += 1;
  if (event.payload.success) {
    state.successfulVerdicts += 1;
  }

  if (event.roundNumber !== null && state.roundVerdicts[event.roundNumber]) {
    const rv = state.roundVerdicts[event.roundNumber];
    if (event.payload.success) {
      rv.pass += 1;
    } else {
      rv.fail += 1;
    }
    updateRoundButtonLabel(event.roundNumber);
    updateRoundComparison();
  }

  if (state.activeScenarioKey) {
    state.scenarioMetadata[state.activeScenarioKey].verdict = event.payload;
    updateScenarioTabVerdict(state.activeScenarioKey, event.payload);
  }

  updateVerdictCard(event.payload);
}

function incrementMetric(metric) {
  state.scenarioMetrics[ALL_FILTER][metric] += 1;
  if (state.activeScenarioKey) {
    state.scenarioMetrics[state.activeScenarioKey][metric] += 1;
  }
}

function renderIfVisible(event, renderFunction) {
  if (shouldRenderEvent(event)) {
    renderFunction(event.payload);
  }
}

function shouldRenderEvent(event) {
  if (!eventMatchesRoundFilter(event.roundNumber)) {
    return false;
  }

  return state.currentScenario === state.activeScenarioKey;
}

function switchRound(roundFilter) {
  state.currentRoundFilter = roundFilter;
  updateRoundButtons();
  updateScenarioTabVisibility();

  if (!state.currentScenario || !scenarioMatchesRoundFilter(state.currentScenario)) {
    const firstVisible = elements.scenarioTabs.querySelector(".scenario-tab:not(.hidden)");
    state.currentScenario = firstVisible ? firstVisible.dataset.scenario : null;
  }

  updateActiveScenarioTab();
  rerenderConversation();
  updateVerdictForCurrentScenario();
  renderAdaptationCard();
  updateMetrics();
  updateHeaderSummary();
}

function switchTab(scenarioKey) {
  state.currentScenario = scenarioKey;
  updateActiveScenarioTab();
  rerenderConversation();
  updateVerdictForCurrentScenario();
  renderAdaptationCard();
  updateMetrics();
  updateHeaderSummary();
}

function updateVerdictForCurrentScenario() {
  const meta = state.scenarioMetadata[state.currentScenario];
  if (meta && meta.verdict) {
    updateVerdictCard(meta.verdict);
  } else {
    clearVerdictCard();
  }
}

function updateRoundButtons() {
  elements.roundSelector.querySelectorAll(".round-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.round === state.currentRoundFilter);
  });
}

function updateScenarioTabVisibility() {
  elements.scenarioTabs.querySelectorAll(".scenario-tab").forEach((tab) => {
    tab.classList.toggle("hidden", !scenarioMatchesRoundFilter(tab.dataset.scenario));
  });
}

function updateActiveScenarioTab() {
  elements.scenarioTabs.querySelectorAll(".scenario-tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.scenario === state.currentScenario);
  });
}

function updateScenarioTabVerdict(scenarioKey, verdict) {
  const tab = elements.scenarioTabs.querySelector(`[data-scenario="${scenarioKey}"]`);
  if (!tab) {
    return;
  }

  const dot = tab.querySelector(".round-dot");
  if (dot) {
    dot.className = verdict.success ? "round-dot round-dot-breached" : "round-dot round-dot-defended";
  }

  const existing = tab.querySelector(".tab-verdict");
  if (existing) {
    existing.remove();
  }

  const badge = document.createElement("span");
  badge.className = verdict.success
    ? "tab-verdict tab-verdict-breached"
    : "tab-verdict tab-verdict-defended";
  badge.textContent = verdict.success ? "BREACHED" : "DEFENDED";
  tab.append(badge);
}

function rerenderConversation() {
  elements.conversation.innerHTML = "";
  state.scenarioEmptyPlaceholder = null;

  const events = filteredEventsForCurrentView();

  if (events.length === 0) {
    const empty = document.createElement("div");
    empty.className = "flex h-full items-center justify-center text-sm text-zinc-500";
    empty.textContent = "No events for this selection";
    elements.conversation.append(empty);
    state.scenarioEmptyPlaceholder = empty;
    return;
  }

  for (const event of events) {
    if (event.event_type === "attacker_reasoning") {
      appendAttackerReasoning(event.payload);
    } else if (event.event_type === "conversation_turn") {
      appendConversationTurn(event.payload);
    } else if (event.event_type === "tool_call") {
      appendToolCall(event.payload);
    } else if (event.event_type === "tool_result") {
      appendToolResult(event.payload);
    } else if (event.event_type === "defender_decision") {
      appendDefenderDecision(event.payload);
    } else if (event.event_type === "content_filter") {
      appendContentFilter(event.payload);
    }
  }

  scrollConversationToBottom();
}

function filteredEventsForCurrentView() {
  const events = state.scenarioEvents[state.currentScenario] || [];
  return events.filter((event) => eventMatchesRoundFilter(event.roundNumber));
}

function appendConversationTurn(payload) {
  const isAttacker = payload.role === "user";
  const bubble = document.createElement("article");
  bubble.className = isAttacker ? "message-row message-row-left" : "message-row message-row-right";

  const content = document.createElement("div");
  content.className = isAttacker ? "message-bubble attacker-bubble" : "message-bubble system-bubble";

  const label = document.createElement("p");
  label.className = "message-label";
  label.textContent = roleLabel(payload.role);

  const text = document.createElement("p");
  text.className = "message-text";
  text.textContent = payload.content;

  content.append(label, text);
  bubble.append(content);
  appendConversationNode(bubble);
}

function appendToolCall(payload) {
  const row = document.createElement("div");
  row.className = "message-row message-row-right";

  const details = document.createElement("details");
  details.className = "tool-card";
  details.open = true;

  const summary = document.createElement("summary");
  summary.className = "tool-summary";
  summary.textContent = `Tool call: ${payload.tool_name}`;

  const code = document.createElement("pre");
  code.className = "tool-code";
  code.textContent = JSON.stringify(payload.arguments, null, 2);

  details.append(summary, code);
  row.append(details);
  appendConversationNode(row);
}

function appendToolResult(payload) {
  const row = document.createElement("div");
  row.className = "message-row message-row-right";

  const details = document.createElement("details");
  details.className = "tool-card tool-result";
  details.open = true;

  const summary = document.createElement("summary");
  summary.className = "tool-summary";
  summary.textContent = `Tool result: ${payload.tool_name}`;

  const code = document.createElement("pre");
  code.className = "tool-code";
  code.textContent = JSON.stringify(payload.result, null, 2);

  details.append(summary, code);
  row.append(details);
  appendConversationNode(row);
}

function appendDefenderDecision(payload) {
  const isBlock = payload.decision === "BLOCK";
  const row = document.createElement("div");
  row.className = "message-row message-row-right";

  const details = document.createElement("details");
  details.className = isBlock ? "defender-card defender-card-block" : "defender-card defender-card-allow";
  details.open = isBlock;

  const summary = document.createElement("summary");
  summary.className = "defender-summary";

  const badge = document.createElement("span");
  badge.className = isBlock ? "defender-badge defender-badge-block" : "defender-badge defender-badge-allow";
  badge.textContent = isBlock ? "BLOCKED" : "ALLOWED";

  const checkpoint = document.createElement("span");
  checkpoint.className = "defender-checkpoint";
  checkpoint.textContent = formatCheckpoint(payload.checkpoint, payload.tool_name);

  summary.append(badge, checkpoint);

  const reason = document.createElement("p");
  reason.className = "defender-reason";
  reason.textContent = payload.reason;

  details.append(summary, reason);

  if (payload.tool_arguments) {
    const argsEl = document.createElement("pre");
    argsEl.className = "tool-code";
    argsEl.textContent = JSON.stringify(payload.tool_arguments, null, 2);
    details.append(argsEl);
  }

  const matchedPatterns = payload.matched_patterns || [];
  if (matchedPatterns.length > 0) {
    details.append(createDefenderDetail("Matched", matchedPatterns.join(", ")));
  }

  if (payload.confidence !== null && payload.confidence !== undefined) {
    const confidence = `${Math.round(payload.confidence * 100)}%`;
    details.append(createDefenderDetail("Confidence", confidence));
  }

  row.append(details);
  appendConversationNode(row);
}

function createDefenderDetail(label, value) {
  const row = document.createElement("p");
  row.className = "defender-detail";

  const labelEl = document.createElement("span");
  labelEl.className = "defender-detail-label";
  labelEl.textContent = label;

  const valueEl = document.createElement("span");
  valueEl.textContent = value;

  row.append(labelEl, valueEl);
  return row;
}

function appendConversationNode(node) {
  if (state.scenarioEmptyPlaceholder) {
    state.scenarioEmptyPlaceholder.remove();
    state.scenarioEmptyPlaceholder = null;
  }

  const shouldScroll = isConversationNearBottom();
  elements.conversation.append(node);

  if (shouldScroll) {
    scrollConversationToBottom();
  } else {
    elements.scrollButton.classList.remove("hidden");
  }
}

function updateMetrics() {
  const defended = state.verdicts - state.successfulVerdicts;
  const defenseRate = state.verdicts === 0 ? 0 : Math.round((defended / state.verdicts) * 100);
  const blockRate =
    state.defenderDecisions === 0 ? 0 : Math.round((state.defenderBlocks / state.defenderDecisions) * 100);
  const metrics = state.scenarioMetrics[ALL_FILTER];

  elements.roundMetric.textContent = state.rounds.length;
  elements.scenarioMetric.textContent = state.scenarios;
  elements.messageMetric.textContent = metrics.messages;
  elements.toolCallMetric.textContent = metrics.toolCalls;
  elements.successRateMetric.textContent = `${defenseRate}%`;
  elements.blockMetric.textContent = state.defenderBlocks;
  elements.blockRateMetric.textContent = `${blockRate}%`;
}

function updateHeaderSummary() {
  if (state.currentScenario) {
    const meta = state.scenarioMetadata[state.currentScenario];
    if (meta) {
      const name = humanizeName(meta.name);
      if (meta.verdict) {
        const status = meta.verdict.success ? "BREACHED" : "DEFENDED";
        elements.headerSummary.textContent = `${name} \u2014 ${status}`;
      } else {
        elements.headerSummary.textContent = `${name} \u2014 in progress`;
      }
    }
    return;
  }

  if (state.events > 0) {
    elements.headerSummary.textContent = `${state.events} events`;
  } else {
    elements.headerSummary.textContent = "Waiting for arena events";
  }
}

function setStatus(label, status) {
  elements.statusBadge.textContent = label;
  elements.statusBadge.className = "rounded-full border px-3 py-1 text-sm";

  if (status === "running") {
    elements.statusBadge.classList.add("border-emerald-500/40", "bg-emerald-500/10", "text-emerald-300");
    return;
  }

  if (status === "completed") {
    elements.statusBadge.classList.add("border-sky-500/40", "bg-sky-500/10", "text-sky-300");
    return;
  }

  elements.statusBadge.classList.add("border-zinc-700", "text-zinc-300");
}

function resetState() {
  state.events = 0;
  state.scenarios = 0;
  state.verdicts = 0;
  state.successfulVerdicts = 0;
  state.defenderDecisions = 0;
  state.defenderBlocks = 0;
  state.currentScenario = null;
  state.currentRoundFilter = null;
  state.currentRoundNumber = null;
  state.activeScenarioKey = null;
  state.rounds = [];
  state.roundVerdicts = {};
  state.scenarioEvents = { [ALL_FILTER]: [] };
  state.scenarioEmptyPlaceholder = null;
  state.scenarioMetadata = {};
  state.scenarioMetrics = { [ALL_FILTER]: { messages: 0, toolCalls: 0, toolResults: 0 } };

  state.reflections = [];
  state.briefings = {};

  elements.roundSelector.querySelectorAll(".round-button").forEach((button) => button.remove());
  elements.scenarioTabs.querySelectorAll(".scenario-tab").forEach((tab) => tab.remove());

  elements.conversation.innerHTML = "";
  elements.emptyState = null;
  elements.headerSummary.textContent = "Waiting for arena events";
  clearVerdictCard();
  elements.roundComparison.innerHTML = "";
  elements.roundComparisonCard.classList.add("hidden");
  elements.adaptationContent.innerHTML = "";
  elements.adaptationCard.classList.add("hidden");
  setStatus("Idle", "idle");
  updateMetrics();
}

function removeEmptyState() {
  if (elements.emptyState !== null) {
    elements.emptyState.remove();
    elements.emptyState = null;
  }
}

function roleLabel(role) {
  if (role === "user") {
    return "Attacker";
  }

  if (role === "assistant") {
    return "Shielded System";
  }

  return "System";
}

function humanizeName(snakeName) {
  return snakeName
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function formatCheckpoint(checkpoint, toolName) {
  if (checkpoint === "on_user_input") {
    return "Input checkpoint";
  }

  if (checkpoint === "on_tool_call") {
    return toolName ? `Tool-call checkpoint: ${toolName}` : "Tool-call checkpoint";
  }

  return checkpoint;
}

function buildScenarioKey(roundNumber, scenarioName) {
  if (roundNumber === null) {
    return `standalone:${scenarioName}:${state.scenarios + 1}`;
  }

  return `round-${roundNumber}:${scenarioName}`;
}

function scenarioMatchesRoundFilter(scenarioKey) {
  if (state.currentRoundFilter === null) {
    return true;
  }

  const metadata = state.scenarioMetadata[scenarioKey];
  return metadata !== undefined && String(metadata.roundNumber) === state.currentRoundFilter;
}

function eventMatchesRoundFilter(roundNumber) {
  return state.currentRoundFilter === null || String(roundNumber) === state.currentRoundFilter;
}

function createVerdictField(label, value) {
  const row = document.createElement("div");
  row.className = "verdict-field";

  const labelEl = document.createElement("span");
  labelEl.className = "verdict-field-label";
  labelEl.textContent = label;

  const valueEl = document.createElement("span");
  valueEl.className = "verdict-field-value";
  valueEl.textContent = value;

  row.append(labelEl, valueEl);
  return row;
}

function createSeverityField(severity) {
  const row = document.createElement("div");
  row.className = "verdict-field";

  const labelEl = document.createElement("span");
  labelEl.className = "verdict-field-label";
  labelEl.textContent = "Severity";

  const badge = document.createElement("span");
  const level = severity.toLowerCase();
  badge.className = `verdict-severity-badge verdict-severity-${level}`;
  badge.textContent = severity;

  const valueEl = document.createElement("span");
  valueEl.className = "verdict-field-value";
  valueEl.appendChild(badge);

  row.append(labelEl, valueEl);
  return row;
}

function updateVerdictCard(payload) {
  const card = elements.verdictCard;
  card.className = payload.success ? "verdict-card verdict-card-breached" : "verdict-card verdict-card-defended";

  const title = document.createElement("p");
  title.className = "verdict-card-title";
  title.textContent = payload.success ? "Attack succeeded" : "Attack failed";

  card.innerHTML = "";
  card.appendChild(title);

  const hasFields = payload.violation_type || payload.violated_rule || payload.evidence || payload.severity;

  if (!hasFields) {
    const noViolation = document.createElement("p");
    noViolation.className = "verdict-card-details";
    noViolation.textContent = "No violation was detected.";
    card.appendChild(noViolation);
    return;
  }

  if (payload.violation_type) {
    card.appendChild(createVerdictField("Violation", payload.violation_type));
  }
  if (payload.violated_rule) {
    card.appendChild(createVerdictField("Rule", payload.violated_rule));
  }
  if (payload.evidence) {
    card.appendChild(createVerdictField("Evidence", payload.evidence));
  }
  if (payload.severity) {
    card.appendChild(createSeverityField(payload.severity));
  }
}

function clearVerdictCard() {
  elements.verdictCard.className = "mt-4 text-sm text-zinc-500";
  elements.verdictCard.innerHTML = "";
  elements.verdictCard.textContent = "No verdict yet";
}

function isConversationNearBottom() {
  const distanceFromBottom =
    elements.conversation.scrollHeight - elements.conversation.scrollTop - elements.conversation.clientHeight;
  return distanceFromBottom < 80;
}

function scrollConversationToBottom() {
  elements.conversation.scrollTop = elements.conversation.scrollHeight;
  elements.scrollButton.classList.add("hidden");
}

function appendAttackerReasoning(payload) {
  const row = document.createElement("div");
  row.className = "message-row message-row-left";

  const bubble = document.createElement("div");
  bubble.className = "reasoning-bubble";

  const label = document.createElement("p");
  label.className = "reasoning-label";
  label.textContent = "Attacker Reasoning";

  const text = document.createElement("p");
  text.className = "reasoning-text";
  text.textContent = payload.reasoning;

  bubble.append(label, text);
  row.append(bubble);
  appendConversationNode(row);
}

function appendContentFilter(payload) {
  const row = document.createElement("div");
  row.className = "message-row message-row-center";

  const banner = document.createElement("div");
  banner.className = "content-filter-banner";

  const header = document.createElement("div");
  header.className = "content-filter-header";

  const badge = document.createElement("span");
  badge.className = "content-filter-badge";
  badge.textContent = "CONTENT FILTERED";

  const source = document.createElement("span");
  source.className = "content-filter-source";
  source.textContent = humanizeName(payload.source);

  header.append(badge, source);

  const msg = document.createElement("p");
  msg.className = "content-filter-message";
  msg.textContent = payload.message;

  banner.append(header, msg);
  row.append(banner);
  appendConversationNode(row);
}

function handleAttackBriefing(payload) {
  const key = `${payload.strategy_name}:${payload.round_number}`;
  state.briefings[key] = payload;
  renderAdaptationCard();
}

function handleAttackReflection(payload) {
  state.reflections.push(payload);
  renderAdaptationCard();
}

function renderAdaptationCard() {
  const container = elements.adaptationContent;
  container.innerHTML = "";

  if (state.reflections.length === 0) {
    elements.adaptationCard.classList.add("hidden");
    return;
  }

  let visibleReflections = state.reflections;
  if (state.currentScenario) {
    const meta = state.scenarioMetadata[state.currentScenario];
    if (meta) {
      visibleReflections = state.reflections.filter((r) => r.strategy_name === meta.name);
    }
  }
  if (state.currentRoundFilter !== null) {
    const maxRound = parseInt(state.currentRoundFilter, 10);
    visibleReflections = visibleReflections.filter((r) => r.round_number <= maxRound);
  }

  if (visibleReflections.length === 0) {
    elements.adaptationCard.classList.add("hidden");
    return;
  }

  elements.adaptationCard.classList.remove("hidden");

  const strategies = [...new Set(visibleReflections.map((r) => r.strategy_name))];

  for (const strategyName of strategies) {
    const strategyReflections = visibleReflections
      .filter((r) => r.strategy_name === strategyName)
      .sort((a, b) => a.round_number - b.round_number);

    const section = document.createElement("div");
    section.className = "adaptation-strategy";

    const title = document.createElement("p");
    title.className = "adaptation-strategy-title";
    title.textContent = humanizeName(strategyName);
    section.append(title);

    for (let i = 0; i < strategyReflections.length; i++) {
      const reflection = strategyReflections[i];

      if (i > 0) {
        const arrow = document.createElement("div");
        arrow.className = "adaptation-arrow";
        arrow.textContent = "adapted";
        section.append(arrow);
      }

      const entry = document.createElement("div");
      entry.className = reflection.success ? "adaptation-entry adaptation-entry-breached" : "adaptation-entry adaptation-entry-defended";

      const header = document.createElement("p");
      header.className = "adaptation-entry-header";
      header.textContent = `R${reflection.round_number} ${reflection.success ? "BREACHED" : "DEFENDED"}`;
      entry.append(header);

      entry.appendChild(createVerdictField("Tactic", `"${reflection.tactic_used}"`));

      if (reflection.success) {
        entry.appendChild(createVerdictField("Why", reflection.why_outcome));
      } else {
        if (reflection.defensive_trigger) {
          entry.appendChild(createVerdictField("Blocked", reflection.defensive_trigger));
        }

        if (reflection.suggested_mutations && reflection.suggested_mutations.length > 0) {
          const row = document.createElement("div");
          row.className = "verdict-field";

          const label = document.createElement("span");
          label.className = "verdict-field-label";
          label.textContent = "Next moves";

          const value = document.createElement("span");
          value.className = "verdict-field-value";
          const mutList = document.createElement("ol");
          mutList.className = "adaptation-mutations";
          for (const mutation of reflection.suggested_mutations) {
            const li = document.createElement("li");
            li.textContent = mutation;
            mutList.append(li);
          }
          value.appendChild(mutList);
          row.append(label, value);
          entry.appendChild(row);
        }
      }

      section.append(entry);
    }

    container.append(section);
  }
}
