const API_BASE = "http://127.0.0.1:8001/api/v1";
const POLL_INTERVAL_MS = 2000;

const packageIdInput = document.getElementById("package-id-input");
const parseJsonEl = document.getElementById("parse-json");
const generateJsonEl = document.getElementById("generate-json");
const sendParseBtn = document.getElementById("send-parse-btn");
const sendGenerateBtn = document.getElementById("send-generate-btn");
const messagesList = document.getElementById("messages-list");
const statusPill = document.getElementById("status-pill");

let nextOffset = 0;
let pollingTimerId = null;
let activePackageId = "";

function defaultParsePayload() {
  return {
    application_date: "2026-04-23",
    plaintiff_name: "ООО Ромашка",
    defendant_name: "ТСЖ Север",
    claim_amount: 123456.78,
    files: [
      { file_name: "contract.pdf", file_type: "application/pdf", file_size: 120034 },
      { file_name: "claim.pdf", file_type: "application/pdf", file_size: 54012 },
      {
        file_name: "certificate.xlsx",
        file_type:
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        file_size: 40011,
      },
    ],
    notes: "Демо-пакет",
  };
}

function defaultGeneratePayload() {
  const payload = defaultParsePayload();
  payload.notes = `${payload.notes} (отредактировано пользователем)`;
  payload.claim_amount = payload.claim_amount + 1000.0;
  return payload;
}

function setStatus(text) {
  statusPill.textContent = text;
}

function appendMessage(eventObj) {
  const item = document.createElement("div");
  item.className = "message-item";

  const meta = document.createElement("div");
  meta.className = "message-meta";
  meta.textContent = eventObj.timestamp || "-";

  const body = document.createElement("div");
  body.className = "message-json";
  body.textContent = eventObj?.data?.message || "-";

  item.appendChild(meta);
  item.appendChild(body);
  messagesList.appendChild(item);
  messagesList.scrollTop = messagesList.scrollHeight;
}

function clearMessages() {
  messagesList.innerHTML = "";
}

function parseJsonOrThrow(text) {
  try {
    return JSON.parse(text);
  } catch (err) {
    throw new Error(`Некорректный JSON: ${err.message}`);
  }
}

async function ensurePackageId() {
  const existing = packageIdInput.value.trim();
  if (existing) {
    return existing;
  }

  const resp = await fetch(`${API_BASE}/packages`, { method: "POST" });
  if (!resp.ok) {
    throw new Error(`Не удалось создать package: HTTP ${resp.status}`);
  }
  const payload = await resp.json();
  const packageId = payload.package_id;
  packageIdInput.value = packageId;
  return packageId;
}

async function sendParse() {
  try {
    const packageId = await ensurePackageId();
    const payload = parseJsonOrThrow(parseJsonEl.value);
    const resp = await fetch(`${API_BASE}/packages/${packageId}/parse`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      throw new Error(`Parse rejected: HTTP ${resp.status}`);
    }
    startPolling(packageId, true);
    setStatus(`parse accepted (${packageId})`);
  } catch (err) {
    setStatus(`error: ${err.message}`);
    alert(err.message);
  }
}

async function sendGenerate() {
  try {
    const packageId = await ensurePackageId();
    const payload = parseJsonOrThrow(generateJsonEl.value);
    const resp = await fetch(`${API_BASE}/packages/${packageId}/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      throw new Error(`Generate rejected: HTTP ${resp.status}`);
    }
    startPolling(packageId, false);
    setStatus(`generate accepted (${packageId})`);
  } catch (err) {
    setStatus(`error: ${err.message}`);
    alert(err.message);
  }
}

async function pollMessages() {
  const packageId = activePackageId || packageIdInput.value.trim();
  if (!packageId) {
    return;
  }

  try {
    const resp = await fetch(
      `${API_BASE}/packages/${packageId}/events?since=${nextOffset}`,
    );
    if (!resp.ok) {
      setStatus(`poll error: HTTP ${resp.status}`);
      return;
    }
    const payload = await resp.json();
    const events = payload.events || [];
    for (const eventObj of events) {
      appendMessage(eventObj);
    }
    nextOffset = payload.next_offset ?? nextOffset;
    setStatus(`listening package=${packageId} offset=${nextOffset}`);
  } catch (err) {
    setStatus(`poll error: ${err.message}`);
  }
}

function startPolling(packageId, resetOffset) {
  activePackageId = packageId;
  if (resetOffset) {
    nextOffset = 0;
    clearMessages();
  }
  if (pollingTimerId !== null) {
    clearInterval(pollingTimerId);
  }
  pollMessages();
  pollingTimerId = setInterval(pollMessages, POLL_INTERVAL_MS);
}

sendParseBtn.addEventListener("click", sendParse);
sendGenerateBtn.addEventListener("click", sendGenerate);

packageIdInput.addEventListener("change", () => {
  const packageId = packageIdInput.value.trim();
  if (!packageId) {
    return;
  }
  startPolling(packageId, true);
});

parseJsonEl.value = JSON.stringify(defaultParsePayload(), null, 2);
generateJsonEl.value = JSON.stringify(defaultGeneratePayload(), null, 2);
setStatus("idle");
