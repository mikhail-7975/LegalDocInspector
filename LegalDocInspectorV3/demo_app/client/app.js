const API_BASE = "http://127.0.0.1:8001/api/v1";
const POLL_INTERVAL_MS = 2000;

const packageIdInput = document.getElementById("package-id-input");
const parseJsonEl = document.getElementById("parse-json");
const generateJsonEl = document.getElementById("generate-json");
const contractsListEl = document.getElementById("contracts-list");
const addContractBtn = document.getElementById("add-contract-btn");
const contractRowTpl = document.getElementById("tpl-contract-row");
const panelGenerateEl = document.querySelector(".panel-generate");
const sendParseBtn = document.getElementById("send-parse-btn");
const sendGenerateBtn = document.getElementById("send-generate-btn");
const messagesList = document.getElementById("messages-list");
const statusPill = document.getElementById("status-pill");
const appLayout = document.getElementById("app-layout");
const hideMessagesBtn = document.getElementById("hide-messages-btn");
const revealMessagesBtn = document.getElementById("reveal-messages-btn");

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

function getPlaintiffInfoFromDom() {
  const inn = document.getElementById("pi-inn")?.value?.trim() ?? "";
  const full_name = document.getElementById("pi-full_name")?.value?.trim() ?? "";
  const short_name = document.getElementById("pi-short_name")?.value?.trim() ?? "";
  const addres = document.getElementById("pi-addres")?.value?.trim() ?? "";
  const correspondency_addres =
    document.getElementById("pi-correspondency_addres")?.value?.trim() ?? "";
  const ogrn = document.getElementById("pi-ogrn")?.value?.trim() ?? "";
  return { inn, full_name, short_name, addres, correspondency_addres, ogrn };
}

function getDefendantInfoFromDom() {
  const full_name = document.getElementById("di-full_name")?.value?.trim() ?? "";
  const short_name = document.getElementById("di-short_name")?.value?.trim() ?? "";
  const addres = document.getElementById("di-addres")?.value?.trim() ?? "";
  const inn = document.getElementById("di-inn")?.value?.trim() ?? "";
  const ogrn = document.getElementById("di-ogrn")?.value?.trim() ?? "";
  return { full_name, short_name, addres, inn, ogrn };
}

function getContractsFromDom() {
  const rows = contractsListEl.querySelectorAll("[data-contract-row]");
  const contracts = [];
  for (const row of rows) {
    contracts.push({
      contract_type: row.querySelector(".contract-type")?.value?.trim() || "",
      day_of_penalty: row.querySelector(".contract-day")?.value?.trim() || "",
      contract_point: row.querySelector(".contract-point")?.value?.trim() || "",
      claim_info: row.querySelector(".contract-claim")?.value?.trim() || "",
    });
  }
  return contracts;
}

function buildNotesPayload(plaintiff_info, defendant_info, contracts) {
  return JSON.stringify(
    {
      comment: "Демо-пакет (форма generate)",
      plaintiff_info,
      defendant_info,
      contracts,
    },
    null,
    2,
  );
}

function buildGeneratePayloadFromForm() {
  const base = defaultGeneratePayload();
  const plaintiff_info = getPlaintiffInfoFromDom();
  const defendant_info = getDefendantInfoFromDom();
  base.plaintiff_name =
    plaintiff_info.short_name || plaintiff_info.full_name || base.plaintiff_name;
  base.defendant_name =
    defendant_info.short_name || defendant_info.full_name || base.defendant_name;
  base.notes = buildNotesPayload(plaintiff_info, defendant_info, getContractsFromDom());
  return base;
}

function refreshGenerateJsonPreview() {
  generateJsonEl.value = JSON.stringify(buildGeneratePayloadFromForm(), null, 2);
}

function renumberContractTitles() {
  const rows = contractsListEl.querySelectorAll("[data-contract-row]");
  rows.forEach((row, i) => {
    const title = row.querySelector(".contract-row__title");
    if (title) {
      title.textContent = `Договор ${i + 1}`;
    }
  });
}

function addContractRow(preset) {
  const node = contractRowTpl.content.firstElementChild.cloneNode(true);
  if (preset) {
    const typeSel = node.querySelector(".contract-type");
    const dayInp = node.querySelector(".contract-day");
    const pointInp = node.querySelector(".contract-point");
    const claimTa = node.querySelector(".contract-claim");
    if (preset.contract_type && typeSel) {
      const opt = [...typeSel.options].find((o) => o.value === preset.contract_type);
      if (opt) typeSel.value = preset.contract_type;
    }
    if (dayInp && preset.day_of_penalty != null) dayInp.value = preset.day_of_penalty;
    if (pointInp && preset.contract_point != null) pointInp.value = preset.contract_point;
    if (claimTa && preset.claim_info != null) claimTa.value = preset.claim_info;
  }
  contractsListEl.appendChild(node);
  renumberContractTitles();
}

const DEFAULT_PLAINTIFF_INFO = {
  inn: "7720518494",
  full_name:
    "ПУБЛИЧНОЕ АКЦИОНЕРНОЕ ОБЩЕСТВО «МОСКОВСКАЯ ОБЪЕДИНЕННАЯ ЭНЕРГЕТИЧЕСКАЯ КОМПАНИЯ»",
  short_name: "ПАО «МОЭК»",
  addres: "119526, Москва, пр-кт Вернадского, д. 101 к. 3 эт/каб 20/2017",
  correspondency_addres:
    "121596, г. Москва, ул. Горбунова, д. 2, стр. 3, офис В613",
  ogrn: "1047796974092",
};

const DEFAULT_DEFENDANT_INFO = {
  full_name: "ЖСК №3 РАБОТНИКОВ МИДСССР",
  short_name: "ЖСК №3 РАБОТНИКОВ МИДСССР",
  addres: "121099, Г.МОСКВА, Б-Р НОВИНСКИЙ, Д. 15",
  inn: "7704065007",
  ogrn: "1037700251874",
};

function initGenerateForm() {
  document.getElementById("pi-inn").value = DEFAULT_PLAINTIFF_INFO.inn;
  document.getElementById("pi-ogrn").value = DEFAULT_PLAINTIFF_INFO.ogrn;
  document.getElementById("pi-full_name").value = DEFAULT_PLAINTIFF_INFO.full_name;
  document.getElementById("pi-short_name").value = DEFAULT_PLAINTIFF_INFO.short_name;
  document.getElementById("pi-addres").value = DEFAULT_PLAINTIFF_INFO.addres;
  document.getElementById("pi-correspondency_addres").value =
    DEFAULT_PLAINTIFF_INFO.correspondency_addres;

  document.getElementById("di-inn").value = DEFAULT_DEFENDANT_INFO.inn;
  document.getElementById("di-ogrn").value = DEFAULT_DEFENDANT_INFO.ogrn;
  document.getElementById("di-full_name").value = DEFAULT_DEFENDANT_INFO.full_name;
  document.getElementById("di-short_name").value = DEFAULT_DEFENDANT_INFO.short_name;
  document.getElementById("di-addres").value = DEFAULT_DEFENDANT_INFO.addres;

  contractsListEl.innerHTML = "";
  addContractRow({
    contract_type: "ТЭ",
    day_of_penalty: "18",
    contract_point: "4.5",
    claim_info: "№ 567381 от 21.07.2025",
  });
  refreshGenerateJsonPreview();
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
    const payload = buildGeneratePayloadFromForm();
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

addContractBtn.addEventListener("click", () => {
  addContractRow({
    contract_type: "ТЭ",
    day_of_penalty: "",
    contract_point: "",
    claim_info: "",
  });
  refreshGenerateJsonPreview();
});

contractsListEl.addEventListener("click", (ev) => {
  const btn = ev.target.closest(".btn-remove-contract");
  if (!btn) return;
  const row = btn.closest("[data-contract-row]");
  if (!row || contractsListEl.querySelectorAll("[data-contract-row]").length <= 1) {
    return;
  }
  row.remove();
  renumberContractTitles();
  refreshGenerateJsonPreview();
});

function onGenerateFormChange() {
  refreshGenerateJsonPreview();
}

function setMessagesPanelVisible(visible) {
  if (visible) {
    appLayout.classList.remove("layout--messages-hidden");
    revealMessagesBtn.hidden = true;
  } else {
    appLayout.classList.add("layout--messages-hidden");
    revealMessagesBtn.hidden = false;
  }
}

panelGenerateEl.addEventListener("input", onGenerateFormChange);
panelGenerateEl.addEventListener("change", onGenerateFormChange);

hideMessagesBtn.addEventListener("click", () => {
  setMessagesPanelVisible(false);
});

revealMessagesBtn.addEventListener("click", () => {
  setMessagesPanelVisible(true);
});

packageIdInput.addEventListener("change", () => {
  const packageId = packageIdInput.value.trim();
  if (!packageId) {
    return;
  }
  startPolling(packageId, true);
});

parseJsonEl.value = JSON.stringify(defaultParsePayload(), null, 2);
initGenerateForm();
setStatus("idle");
