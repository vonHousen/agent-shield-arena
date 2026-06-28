const state = {
  events: 0,
  currentScenario: "all",
  activeScenarioName: null,
  scenarioEvents: { all: [] },

  scenarios: 0,
  scenarioMetrics: {
    all: { messages: 0, toolCalls: 0, toolResults: 0 },
  },
};

const elements = {
  statusBadge: document.querySelector("#statusBadge"),
  eventCount: document.querySelector("#eventCount"),
  conversation: document.querySelector("#conversation"),
  emptyState: document.querySelector("#emptyState"),
  scrollButton: document.querySelector("#scrollButton"),
  scenarioTabs: document.querySelector("#scenarioTabs"),
  scenarioMetric: document.querySelector("#scenarioMetric"),
  messageMetric: document.querySelector("#messageMetric"),
  toolCallMetric: document.querySelector("#toolCallMetric"),
  latestType: document.querySelector("#latestType"),
  latestTimestamp: document.querySelector("#latestTimestamp"),
};

elements.scrollButton.addEventListener("click", () => {
  scrollConversationToBottom();
});

elements.scenarioTabs.addEventListener("click", (e) => {
  const tab = e.target.closest(".scenario-tab");
  if (tab) {
    switchTab(tab.dataset.scenario);
  }
});

connectWebSocket();

function connectWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws`);

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
    setStatus("Idle", "idle");
    window.setTimeout(connectWebSocket, 1500);
  });

  socket.addEventListener("error", () => {
    socket.close();
  });
}

function renderEvent(event) {
  removeEmptyState();
  state.events += 1;

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

  if (event.event_type === "scenario_started") {
    handleScenarioStarted(event.payload);
    return;
  }

  storeEvent(event);

  if (event.event_type === "conversation_turn") {
    incrementMetric("messages", event);
    if (shouldRenderEvent(event)) {
      appendConversationTurn(event.payload);
    }
  }

  if (event.event_type === "tool_call") {
    incrementMetric("toolCalls", event);
    if (shouldRenderEvent(event)) {
      appendToolCall(event.payload);
    }
  }

  if (event.event_type === "tool_result") {
    incrementMetric("toolResults", event);
    if (shouldRenderEvent(event)) {
      appendToolResult(event.payload);
    }
  }

  updateMetrics();
}

function handleScenarioStarted(payload) {
  const name = payload.scenario_name;
  state.activeScenarioName = name;
  state.scenarios += 1;
  state.scenarioEvents[name] = [];
  state.scenarioMetrics[name] = { messages: 0, toolCalls: 0, toolResults: 0 };

  const tab = document.createElement("button");
  tab.className = "scenario-tab";
  tab.type = "button";
  tab.dataset.scenario = name;
  tab.textContent = humanizeName(name);
  elements.scenarioTabs.append(tab);

  switchTab(name);
}

function storeEvent(event) {
  state.scenarioEvents.all.push(event);
  if (state.activeScenarioName) {
    state.scenarioEvents[state.activeScenarioName].push(event);
  }
}

function incrementMetric(metric, event) {
  state.scenarioMetrics.all[metric] += 1;
  if (state.activeScenarioName) {
    state.scenarioMetrics[state.activeScenarioName][metric] += 1;
  }
}

function shouldRenderEvent() {
  if (state.currentScenario === "all") {
    return true;
  }
  return state.currentScenario === state.activeScenarioName;
}

function switchTab(scenarioName) {
  state.currentScenario = scenarioName;

  elements.scenarioTabs.querySelectorAll(".scenario-tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.scenario === scenarioName);
  });

  rerenderConversation();
  updateMetrics();
}

function rerenderConversation() {
  elements.conversation.innerHTML = "";

  const events = state.scenarioEvents[state.currentScenario] || [];

  if (events.length === 0) {
    const empty = document.createElement("div");
    empty.className = "flex h-full items-center justify-center text-sm text-zinc-500";
    empty.textContent = "No events for this scenario";
    elements.conversation.append(empty);
    return;
  }

  for (const event of events) {
    if (event.event_type === "conversation_turn") {
      appendConversationTurn(event.payload);
    } else if (event.event_type === "tool_call") {
      appendToolCall(event.payload);
    } else if (event.event_type === "tool_result") {
      appendToolResult(event.payload);
    }
  }

  scrollConversationToBottom();
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

function appendConversationNode(node) {
  const shouldScroll = isConversationNearBottom();
  elements.conversation.append(node);

  if (shouldScroll) {
    scrollConversationToBottom();
  } else {
    elements.scrollButton.classList.remove("hidden");
  }
}

function updateMetrics() {
  const metrics = state.scenarioMetrics.all;
  elements.scenarioMetric.textContent = state.scenarios;
  elements.messageMetric.textContent = metrics.messages;
  elements.toolCallMetric.textContent = metrics.toolCalls;
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
  state.currentScenario = "all";
  state.activeScenarioName = null;
  state.scenarioEvents = { all: [] };
  state.scenarioMetrics = { all: { messages: 0, toolCalls: 0, toolResults: 0 } };

  elements.scenarioTabs.querySelectorAll('.scenario-tab:not([data-scenario="all"])').forEach((tab) => tab.remove());
  elements.scenarioTabs.querySelector('[data-scenario="all"]').classList.add("active");

  elements.conversation.innerHTML = "";
  elements.emptyState = null;
  elements.eventCount.textContent = "0 events";
  elements.latestType.textContent = "None";
  elements.latestTimestamp.textContent = "None";
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
