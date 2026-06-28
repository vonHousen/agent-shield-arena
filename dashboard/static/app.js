const RUNS_POLL_INTERVAL_MS = 5000;
const ALL_FILTER = "all";

const state = {
  events: 0,
  currentScenario: ALL_FILTER,
  currentRoundFilter: ALL_FILTER,
  currentRoundNumber: null,
  activeScenarioKey: null,
  scenarioEvents: { [ALL_FILTER]: [] },
  scenarioEmptyPlaceholder: null,
  lastRenderedRound: null,

  rounds: [],
  roundVerdicts: {},
  scenarios: 0,
  verdicts: 0,
  successfulVerdicts: 0,
  scenarioMetadata: {},
  scenarioMetrics: {
    [ALL_FILTER]: { messages: 0, toolCalls: 0, toolResults: 0 },
  },

  selectedRun: "latest",
  socket: null,
};

const elements = {
  statusBadge: document.querySelector("#statusBadge"),
  eventCount: document.querySelector("#eventCount"),
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
  latestType: document.querySelector("#latestType"),
  latestTimestamp: document.querySelector("#latestTimestamp"),
  runSelector: document.querySelector("#runSelector"),
  roundComparisonCard: document.querySelector("#roundComparisonCard"),
  roundComparison: document.querySelector("#roundComparison"),
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
  elements.eventCount.textContent = formatCount(state.events, "event");
  elements.latestType.textContent = event.event_type;
  elements.latestTimestamp.textContent = formatTimestamp(event.timestamp);

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
    return;
  }

  if (event.event_type === "scenario_started") {
    handleScenarioStarted(event.payload);
    updateMetrics();
    return;
  }

  storeEvent(event);
  handleConversationEvent(event);
  updateMetrics();
}

function handleRoundStarted(payload) {
  state.currentRoundNumber = payload.round_number;

  if (!state.rounds.includes(payload.round_number)) {
    state.rounds.push(payload.round_number);
    state.roundVerdicts[payload.round_number] = { pass: 0, fail: 0, total: payload.strategy_count };
    addRoundButton(payload.round_number);
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
    label.textContent = `Round ${roundNumber} (${rv.pass}/${evaluated})`;
  }

  const dot = button.querySelector(".round-dot");
  if (dot) {
    dot.className = "round-dot";
    if (evaluated >= rv.total) {
      dot.classList.add(rv.fail === 0 ? "round-dot-pass" : "round-dot-fail");
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

    const passPercent = Math.round((rv.pass / evaluated) * 100);

    const row = document.createElement("div");
    row.className = "comparison-row";

    const labelEl = document.createElement("span");
    labelEl.className = "comparison-label";
    labelEl.textContent = `Round ${roundNumber}`;

    const barTrack = document.createElement("div");
    barTrack.className = "comparison-track";

    const barFill = document.createElement("div");
    barFill.className = "comparison-bar";
    barFill.style.width = `${passPercent}%`;

    if (evaluated < rv.total) {
      barFill.classList.add("comparison-bar-running");
    }

    barTrack.append(barFill);

    const countEl = document.createElement("span");
    countEl.className = "comparison-count";
    countEl.textContent = `${rv.pass}/${evaluated} passed`;

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

  const label = document.createElement("span");
  const prefix = roundNumber !== null ? `R${roundNumber}: ` : "";
  label.textContent = prefix + humanizeName(payload.scenario_name);
  tab.append(label);
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

  if (event.event_type === "evaluation_verdict") {
    handleEvaluationVerdict(event);
  }
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

  renderIfVisible(event, appendEvaluationVerdict);
}

function incrementMetric(metric) {
  state.scenarioMetrics[ALL_FILTER][metric] += 1;
  if (state.activeScenarioKey) {
    state.scenarioMetrics[state.activeScenarioKey][metric] += 1;
  }
}

function renderIfVisible(event, renderFunction) {
  if (shouldRenderEvent(event)) {
    if (state.currentScenario === ALL_FILTER && event.roundNumber !== state.lastRenderedRound) {
      appendRoundHeader(event.roundNumber);
      state.lastRenderedRound = event.roundNumber;
    }
    renderFunction(event.payload);
  }
}

function shouldRenderEvent(event) {
  if (!eventMatchesRoundFilter(event.roundNumber)) {
    return false;
  }

  if (state.currentScenario === ALL_FILTER) {
    return true;
  }
  return state.currentScenario === state.activeScenarioKey;
}

function switchRound(roundFilter) {
  state.currentRoundFilter = roundFilter;
  updateRoundButtons();
  updateScenarioTabVisibility();

  if (state.currentScenario !== ALL_FILTER && !scenarioMatchesRoundFilter(state.currentScenario)) {
    state.currentScenario = ALL_FILTER;
  }

  updateActiveScenarioTab();
  rerenderConversation();
  updateMetrics();
}

function switchTab(scenarioKey) {
  state.currentScenario = scenarioKey;
  updateActiveScenarioTab();
  rerenderConversation();
  updateMetrics();
}

function updateRoundButtons() {
  elements.roundSelector.querySelectorAll(".round-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.round === state.currentRoundFilter);
  });
}

function updateScenarioTabVisibility() {
  elements.scenarioTabs.querySelectorAll(".scenario-tab").forEach((tab) => {
    if (tab.dataset.scenario === ALL_FILTER) {
      tab.classList.remove("hidden");
      return;
    }

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

  const existing = tab.querySelector(".tab-verdict");
  if (existing) {
    existing.remove();
  }

  const badge = document.createElement("span");
  badge.className = verdict.success
    ? "tab-verdict tab-verdict-success"
    : "tab-verdict tab-verdict-failure";
  badge.textContent = verdict.success ? "PASS" : "FAIL";
  tab.append(badge);
}

function rerenderConversation() {
  elements.conversation.innerHTML = "";
  state.scenarioEmptyPlaceholder = null;
  state.lastRenderedRound = null;

  const events = filteredEventsForCurrentView();

  if (events.length === 0) {
    const empty = document.createElement("div");
    empty.className = "flex h-full items-center justify-center text-sm text-zinc-500";
    empty.textContent = "No events for this selection";
    elements.conversation.append(empty);
    state.scenarioEmptyPlaceholder = empty;
    return;
  }

  let renderedRound = null;
  for (const event of events) {
    if (state.currentScenario === ALL_FILTER && event.roundNumber !== renderedRound) {
      appendRoundHeader(event.roundNumber);
      renderedRound = event.roundNumber;
    }

    if (event.event_type === "conversation_turn") {
      appendConversationTurn(event.payload);
    } else if (event.event_type === "tool_call") {
      appendToolCall(event.payload);
    } else if (event.event_type === "tool_result") {
      appendToolResult(event.payload);
    } else if (event.event_type === "evaluation_verdict") {
      appendEvaluationVerdict(event.payload);
    }
  }
  state.lastRenderedRound = renderedRound;

  scrollConversationToBottom();
}

function filteredEventsForCurrentView() {
  const events = state.scenarioEvents[state.currentScenario] || [];
  return events.filter((event) => eventMatchesRoundFilter(event.roundNumber));
}

function appendRoundHeader(roundNumber) {
  const header = document.createElement("div");
  header.className = "round-header";

  if (roundNumber === null) {
    header.textContent = "No round";
  } else {
    let text = `Round ${roundNumber}`;
    const rv = state.roundVerdicts[roundNumber];
    if (rv) {
      const evaluated = rv.pass + rv.fail;
      if (evaluated > 0) {
        text += ` \u2014 ${rv.pass}/${evaluated} passed`;
      }
    }
    header.textContent = text;
  }

  appendConversationNode(header);
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

function appendEvaluationVerdict(payload) {
  const banner = document.createElement("section");
  banner.className = payload.success
    ? "verdict-banner verdict-banner-success"
    : "verdict-banner verdict-banner-failure";

  const title = document.createElement("p");
  title.className = "verdict-title";
  title.textContent = payload.success ? "Evaluation verdict: attack succeeded" : "Evaluation verdict: attack failed";

  const details = document.createElement("p");
  details.className = "verdict-text";
  details.textContent = formatVerdictDetails(payload);

  banner.append(title, details);
  appendConversationNode(banner);
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
  if (state.currentRoundFilter !== ALL_FILTER) {
    const roundNum = parseInt(state.currentRoundFilter, 10);
    const roundMetrics = aggregateRoundMetrics(roundNum);
    const rv = state.roundVerdicts[roundNum];
    const evaluated = rv ? rv.pass + rv.fail : 0;
    const successRate = evaluated === 0 ? 0 : Math.round((rv.pass / evaluated) * 100);

    elements.roundMetric.textContent = `${roundNum}`;
    elements.scenarioMetric.textContent = roundMetrics.scenarios;
    elements.messageMetric.textContent = roundMetrics.messages;
    elements.toolCallMetric.textContent = roundMetrics.toolCalls;
    elements.successRateMetric.textContent = `${successRate}%`;
    return;
  }

  const metrics = state.scenarioMetrics[ALL_FILTER];
  const successRate = state.verdicts === 0 ? 0 : Math.round((state.successfulVerdicts / state.verdicts) * 100);

  elements.roundMetric.textContent = state.rounds.length;
  elements.scenarioMetric.textContent = state.scenarios;
  elements.messageMetric.textContent = metrics.messages;
  elements.toolCallMetric.textContent = metrics.toolCalls;
  elements.successRateMetric.textContent = `${successRate}%`;
}

function aggregateRoundMetrics(roundNumber) {
  let messages = 0;
  let toolCalls = 0;
  let scenarios = 0;

  for (const [key, meta] of Object.entries(state.scenarioMetadata)) {
    if (meta.roundNumber === roundNumber) {
      scenarios += 1;
      const m = state.scenarioMetrics[key];
      if (m) {
        messages += m.messages;
        toolCalls += m.toolCalls;
      }
    }
  }

  return { scenarios, messages, toolCalls };
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
  state.currentScenario = ALL_FILTER;
  state.currentRoundFilter = ALL_FILTER;
  state.currentRoundNumber = null;
  state.activeScenarioKey = null;
  state.rounds = [];
  state.roundVerdicts = {};
  state.scenarioEvents = { [ALL_FILTER]: [] };
  state.scenarioEmptyPlaceholder = null;
  state.lastRenderedRound = null;
  state.scenarioMetadata = {};
  state.scenarioMetrics = { [ALL_FILTER]: { messages: 0, toolCalls: 0, toolResults: 0 } };

  elements.roundSelector.querySelectorAll('.round-button:not([data-round="all"])').forEach((button) => button.remove());
  elements.roundSelector.querySelector('[data-round="all"]').classList.add("active");
  elements.scenarioTabs.querySelectorAll('.scenario-tab:not([data-scenario="all"])').forEach((tab) => tab.remove());
  elements.scenarioTabs.querySelector('[data-scenario="all"]').classList.add("active");

  elements.conversation.innerHTML = "";
  elements.emptyState = null;
  elements.eventCount.textContent = "0 events";
  elements.latestType.textContent = "None";
  elements.latestTimestamp.textContent = "None";
  elements.roundComparison.innerHTML = "";
  elements.roundComparisonCard.classList.add("hidden");
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

function buildScenarioKey(roundNumber, scenarioName) {
  if (roundNumber === null) {
    return `standalone:${scenarioName}:${state.scenarios + 1}`;
  }

  return `round-${roundNumber}:${scenarioName}`;
}

function scenarioMatchesRoundFilter(scenarioKey) {
  if (state.currentRoundFilter === ALL_FILTER) {
    return true;
  }

  const metadata = state.scenarioMetadata[scenarioKey];
  return metadata !== undefined && String(metadata.roundNumber) === state.currentRoundFilter;
}

function eventMatchesRoundFilter(roundNumber) {
  return state.currentRoundFilter === ALL_FILTER || String(roundNumber) === state.currentRoundFilter;
}

function formatVerdictDetails(payload) {
  const parts = [];
  if (payload.violation_type) {
    parts.push(payload.violation_type);
  }
  if (payload.violated_rule) {
    parts.push(payload.violated_rule);
  }
  if (payload.evidence) {
    parts.push(payload.evidence);
  }
  if (payload.severity) {
    parts.push(`Severity: ${payload.severity}`);
  }

  if (parts.length === 0) {
    return "No violation was detected.";
  }

  return parts.join(" | ");
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

function formatCount(count, noun) {
  return `${count} ${noun}${count === 1 ? "" : "s"}`;
}

function formatTimestamp(timestamp) {
  return new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(timestamp));
}
