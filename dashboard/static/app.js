const state = {
  events: 0,
  messages: 0,
  toolCalls: 0,
  toolResults: 0,
};

const elements = {
  statusBadge: document.querySelector("#statusBadge"),
  eventCount: document.querySelector("#eventCount"),
  conversation: document.querySelector("#conversation"),
  emptyState: document.querySelector("#emptyState"),
  scrollButton: document.querySelector("#scrollButton"),
  messageMetric: document.querySelector("#messageMetric"),
  toolCallMetric: document.querySelector("#toolCallMetric"),
  toolResultMetric: document.querySelector("#toolResultMetric"),
  latestType: document.querySelector("#latestType"),
  latestTimestamp: document.querySelector("#latestTimestamp"),
};

elements.scrollButton.addEventListener("click", () => {
  scrollConversationToBottom();
});

connectWebSocket();

function connectWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws`);

  socket.addEventListener("open", () => {
    setStatus("Running", "running");
  });

  socket.addEventListener("message", (message) => {
    const event = JSON.parse(message.data);
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

  if (event.event_type === "conversation_turn") {
    state.messages += 1;
    appendConversationTurn(event.payload);
  }

  if (event.event_type === "tool_call") {
    state.toolCalls += 1;
    appendToolCall(event.payload);
  }

  if (event.event_type === "tool_result") {
    state.toolResults += 1;
    appendToolResult(event.payload);
  }

  updateMetrics();
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
  elements.messageMetric.textContent = state.messages;
  elements.toolCallMetric.textContent = state.toolCalls;
  elements.toolResultMetric.textContent = state.toolResults;
}

function setStatus(label, status) {
  elements.statusBadge.textContent = label;
  elements.statusBadge.className = "rounded-full border px-3 py-1 text-sm";

  if (status === "running") {
    elements.statusBadge.classList.add("border-emerald-500/40", "bg-emerald-500/10", "text-emerald-300");
    return;
  }

  elements.statusBadge.classList.add("border-zinc-700", "text-zinc-300");
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
