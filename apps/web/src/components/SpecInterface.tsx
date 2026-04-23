import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  calculate,
  createPackage,
  downloadDocumentBlob,
  generateDocs,
  getExtraction,
  getForm,
  logout,
  putForm,
  startExtract,
  uploadPackage,
} from "../api/client";
import { buildPrimaryPackageSnapshot } from "../lib/buildPrimaryPackageJson";
import { buildPackageUploadFormData } from "../lib/packageUpload";
import { ComplectFiles, emptyComplect, type ComplectFileState } from "./ComplectFiles";
import { LoginScreen } from "./LoginScreen";
import { Icon, SvgSprite } from "./SvgSprite";

type BackendNoticeKind = "info" | "success" | "warning" | "error";

type BackendNotice = {
  id: string;
  kind: BackendNoticeKind;
  title: string;
  body: string;
  code?: string;
};

type AppFormState = {
  court_info: { name: string; addres: string };
  plaintiff_info: {
    full_name: string;
    short_name: string;
    inn: string;
    ogrn: string;
    addres: string;
    correspondency_addres: string;
  };
  defendant_info: {
    full_name: string;
    short_name: string;
    inn: string;
    ogrn: string;
    addres: string;
  };
  lawsuit_info: {
    cost: string;
    tax: string;
    service_type: string;
    claims: string[];
  };
  complects: Record<string, { contract_type: string; contract_point: string; day_of_penalty: string }>;
  company_type: string;
  end_date: string;
  responsitive_name: string;
};

function todayIso(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function emptyForm(): AppFormState {
  return {
    court_info: { name: "", addres: "" },
    plaintiff_info: {
      full_name: "",
      short_name: "",
      inn: "",
      ogrn: "",
      addres: "",
      correspondency_addres: "",
    },
    defendant_info: {
      full_name: "",
      short_name: "",
      inn: "",
      ogrn: "",
      addres: "",
    },
    lawsuit_info: {
      cost: "",
      tax: "",
      service_type: "ТЭ",
      claims: [],
    },
    complects: {},
    company_type: "ТСЖ",
    end_date: "",
    responsitive_name: "",
  };
}

function asStr(v: unknown, fallback = ""): string {
  return v === null || v === undefined ? fallback : String(v);
}

function asClaims(v: unknown): string[] {
  if (Array.isArray(v)) return v.map((x) => String(x));
  if (typeof v === "string" && v.trim()) return [v];
  return [];
}

function formFromApi(raw: Record<string, unknown> | undefined): AppFormState {
  if (!raw) return emptyForm();
  const ci = (raw.court_info as Record<string, unknown>) || {};
  const pi = (raw.plaintiff_info as Record<string, unknown>) || {};
  const di = (raw.defendant_info as Record<string, unknown>) || {};
  const li = (raw.lawsuit_info as Record<string, unknown>) || {};
  const cx = (raw.complects as Record<string, Record<string, unknown>>) || {};
  const complects: AppFormState["complects"] = {};
  for (const [k, v] of Object.entries(cx)) {
    complects[k] = {
      contract_type: asStr(v?.contract_type, "ТЭ"),
      contract_point: asStr(v?.contract_point, ""),
      day_of_penalty: asStr(v?.day_of_penalty, ""),
    };
  }
  return {
    court_info: {
      name: asStr(ci.name),
      addres: asStr(ci.addres),
    },
    plaintiff_info: {
      full_name: asStr(pi.full_name),
      short_name: asStr(pi.short_name),
      inn: asStr(pi.inn),
      ogrn: asStr(pi.ogrn),
      addres: asStr(pi.addres),
      correspondency_addres: asStr(pi.correspondency_addres),
    },
    defendant_info: {
      full_name: asStr(di.full_name),
      short_name: asStr(di.short_name),
      inn: asStr(di.inn),
      ogrn: asStr(di.ogrn),
      addres: asStr(di.addres ?? di.address),
    },
    lawsuit_info: {
      cost: asStr(li.cost),
      tax: asStr(li.tax),
      service_type: asStr(li.service_type, "ТЭ"),
      claims: asClaims(li.claims),
    },
    complects,
    company_type: asStr(raw.company_type, "ТСЖ"),
    end_date: asStr(raw.end_date),
    responsitive_name: asStr(raw.responsitive_name),
  };
}

function formToApiPayload(f: AppFormState): Record<string, unknown> {
  return {
    court_info: { ...f.court_info },
    plaintiff_info: { ...f.plaintiff_info },
    defendant_info: { ...f.defendant_info },
    lawsuit_info: {
      ...f.lawsuit_info,
      claims: [...f.lawsuit_info.claims],
    },
    complects: { ...f.complects },
    company_type: f.company_type,
    end_date: f.end_date,
    responsitive_name: f.responsitive_name,
  };
}

const PIPELINE: { key: string; label: string }[] = [
  { key: "created", label: "created" },
  { key: "files_uploaded", label: "files_uploaded" },
  { key: "extracting", label: "extracting" },
  { key: "extracted", label: "extracted" },
  { key: "form_editing", label: "form_editing" },
  { key: "calculating", label: "calculating" },
  { key: "calculated", label: "calculated" },
  { key: "generating", label: "generating" },
  { key: "documents_ready", label: "documents_ready" },
];

function newNoticeId() {
  return crypto.randomUUID();
}

export default function SpecInterface() {
  const [authenticated, setAuthenticated] = useState(false);
  const [userLabel, setUserLabel] = useState("");

  const [applicationDateIso, setApplicationDateIso] = useState(todayIso);
  const [endDateText, setEndDateText] = useState("");
  const [companyType, setCompanyType] = useState("ТСЖ");

  const [packageId, setPackageId] = useState<string | null>(null);
  const [packageState, setPackageState] = useState<string>("—");

  const [egrulFile, setEgrulFile] = useState<File | null>(null);
  const [complects, setComplects] = useState<ComplectFileState[]>(() => [emptyComplect()]);

  const [formState, setFormState] = useState<AppFormState>(emptyForm);
  const [parseResult, setParseResult] = useState<Record<string, unknown> | null>(null);

  const [extractBusy, setExtractBusy] = useState(false);
  const [calcBusy, setCalcBusy] = useState(false);
  const [genBusy, setGenBusy] = useState(false);

  const [polling, setPolling] = useState(false);
  const pollTimerRef = useRef<number | null>(null);
  const lastPollStateRef = useRef<string | null>(null);

  const [notifCollapsed, setNotifCollapsed] = useState(false);
  const [notices, setNotices] = useState<BackendNotice[]>([]);

  const [toasts, setToasts] = useState<
    { id: string; kind: "info" | "warning"; title: string; body: string }[]
  >([]);

  const pushNotice = useCallback((n: Omit<BackendNotice, "id">) => {
    setNotices((prev) => [{ id: newNoticeId(), ...n }, ...prev].slice(0, 80));
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute("data-mock-ui", "legaldocinspector-v1");
  }, []);

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current !== null) {
      window.clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
    setPolling(false);
  }, []);

  const loadFormAfterExtract = useCallback(async (pid: string) => {
    try {
      const data = await getForm(pid);
      const next = formFromApi(data.form as Record<string, unknown>);
      setFormState(next);
      setCompanyType(next.company_type);
      setEndDateText(next.end_date);
      const pr = (data.parseResult ?? null) as Record<string, unknown> | null;
      setParseResult(pr);

      const rawWarnings = pr?.parse_warnings;
      const warningLines = Array.isArray(rawWarnings)
        ? rawWarnings.filter((x): x is string => typeof x === "string" && x.trim().length > 0)
        : [];

      pushNotice({
        kind: "success",
        title: "Извлечение завершено",
        body: "Данные формы обновлены из результата разбора.",
      });
      for (let i = warningLines.length - 1; i >= 0; i -= 1) {
        pushNotice({
          kind: "warning",
          title: "Предупреждение разбора",
          body: warningLines[i].trim(),
        });
      }
    } catch (e) {
      pushNotice({
        kind: "error",
        title: "Не удалось загрузить форму",
        body: e instanceof Error ? e.message : String(e),
      });
    }
  }, [pushNotice]);

  const onLoggedIn = useCallback((label: string) => {
    setUserLabel(label);
    setAuthenticated(true);
    setNotices([]);
    pushNotice({ kind: "info", title: "Сессия", body: "Вы вошли в систему." });
  }, [pushNotice]);

  const onLogout = useCallback(async () => {
    try {
      await logout();
    } catch {
      /* ignore */
    }
    stopPolling();
    setAuthenticated(false);
    setUserLabel("");
    setPackageId(null);
    setPackageState("—");
    setFormState(emptyForm());
    setParseResult(null);
    setEgrulFile(null);
    setComplects([emptyComplect()]);
    setNotices([]);
    setExtractBusy(false);
  }, [stopPolling]);

  useEffect(() => {
    if (!authenticated) return;
    const dirty =
      !!egrulFile ||
      complects.some(
        (c) => c.contract || c.preClaim || c.certificates.some(Boolean)
      ) ||
      !!packageId;
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      if (!dirty) return;
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [authenticated, complects, egrulFile, packageId]);

  const beginPollExtraction = useCallback(
    (pid: string) => {
      stopPolling();
      setPolling(true);
      lastPollStateRef.current = null;
      const tick = async () => {
        try {
          const st = await getExtraction(pid);
          setPackageState(st.state);
          if (st.state === "extracting" && lastPollStateRef.current !== "extracting") {
            lastPollStateRef.current = "extracting";
            pushNotice({
              kind: "info",
              title: "Извлечение",
              body: "Обработка пакета на сервере…",
            });
          }
          if (st.state === "extracted") {
            stopPolling();
            setExtractBusy(false);
            await loadFormAfterExtract(pid);
            return;
          }
          if (st.state === "failed") {
            stopPolling();
            setExtractBusy(false);
            pushNotice({
              kind: "error",
              title: "Ошибка извлечения",
              body: st.error || "Неизвестная ошибка",
            });
            return;
          }
          lastPollStateRef.current = st.state;
        } catch (e) {
          pushNotice({
            kind: "error",
            title: "Ошибка опроса статуса",
            body: e instanceof Error ? e.message : String(e),
          });
        }
      };
      void tick();
      pollTimerRef.current = window.setInterval(() => void tick(), 2000);
    },
    [loadFormAfterExtract, pushNotice, stopPolling]
  );

  useEffect(() => () => stopPolling(), [stopPolling]);

  const onRunExtract = useCallback(async () => {
    if (!authenticated) return;
    setExtractBusy(true);
    try {
      if (!egrulFile) {
        throw new Error("Загрузите выписку ЕГРЮЛ (PDF)");
      }
      const fd = buildPackageUploadFormData({
        applicationDateIso,
        egrul: egrulFile,
        complects,
      });

      let pid = packageId;
      if (!pid) {
        const created = await createPackage();
        pid = created.packageId;
        setPackageId(pid);
        setPackageState(created.state);
        pushNotice({
          kind: "info",
          title: "Пакет создан",
          body: `packageId: ${pid}`,
        });
      }

      const up = await uploadPackage(pid, fd);
      setPackageState(up.state ?? "files_uploaded");
      pushNotice({
        kind: "success",
        title: "Файлы отправлены",
        body: "Метаданные и документы приняты сервером.",
      });

      const primary = buildPrimaryPackageSnapshot({
        packageId: pid,
        applicationDateIso,
        companyType,
        endDateOverdue: endDateText,
        egrulFileName: egrulFile.name,
        complects: complects.map((c) => ({
          contractFileName: c.contract?.name ?? null,
          preClaimFileName: c.preClaim?.name ?? null,
          debtCertificateFileNames: c.certificates
            .filter((f): f is File => f !== null)
            .map((f) => f.name),
        })),
      });

      pushNotice({
        kind: "info",
        title: "Запуск извлечения",
        body: "На сервер отправлен JSON первичных данных (снимок пакета) в теле POST /extract.",
        code: JSON.stringify(primary).slice(0, 280) + (JSON.stringify(primary).length > 280 ? "…" : ""),
      });

      const ex = await startExtract(pid, primary as unknown as Record<string, unknown>);
      setPackageState(ex.state);
      beginPollExtraction(pid);
    } catch (e) {
      setExtractBusy(false);
      pushNotice({
        kind: "error",
        title: "Извлечение не запущено",
        body: e instanceof Error ? e.message : String(e),
      });
    }
  }, [
    authenticated,
    applicationDateIso,
    beginPollExtraction,
    companyType,
    complects,
    egrulFile,
    endDateText,
    packageId,
    pushNotice,
  ]);

  const onCalculateOnly = useCallback(async () => {
    if (!packageId) {
      pushNotice({ kind: "warning", title: "Нет пакета", body: "Сначала выполните извлечение." });
      return;
    }
    setCalcBusy(true);
    try {
      await putForm(packageId, formToApiPayload({ ...formState, company_type: companyType, end_date: endDateText }));
      const r = await calculate(packageId);
      setFormState(formFromApi(r.form as Record<string, unknown>));
      setPackageState("calculated");
      pushNotice({
        kind: "success",
        title: "Расчёт выполнен",
        body: "Данные формы и суммы обновлены.",
      });
    } catch (e) {
      pushNotice({
        kind: "error",
        title: "Ошибка расчёта",
        body: e instanceof Error ? e.message : String(e),
      });
    } finally {
      setCalcBusy(false);
    }
  }, [companyType, endDateText, formState, packageId, pushNotice]);

  const onGenerateDocs = useCallback(async () => {
    if (!packageId) {
      pushNotice({ kind: "warning", title: "Нет пакета", body: "Сначала выполните извлечение." });
      return;
    }
    setGenBusy(true);
    try {
      const merged = { ...formState, company_type: companyType, end_date: endDateText };
      await putForm(packageId, formToApiPayload(merged));
      pushNotice({
        kind: "info",
        title: "Сохранение формы",
        body: "Актуальные данные формы (истец, ответчик, суд, иск) отправлены на сервер (PUT /form).",
      });
      const calcOut = await calculate(packageId);
      setFormState(formFromApi(calcOut.form as Record<string, unknown>));
      const gen = await generateDocs(packageId);
      setPackageState(gen.state ?? "documents_ready");
      const iskBlob = await downloadDocumentBlob(packageId, "isk");
      const calcBlob = await downloadDocumentBlob(packageId, "calculation");
      const iskName = gen.isk || `isk_${packageId}.docx`;
      const calcName = gen.calculation || `calculation_${packageId}.docx`;
      const u1 = URL.createObjectURL(iskBlob);
      const u2 = URL.createObjectURL(calcBlob);
      const a1 = document.createElement("a");
      a1.href = u1;
      a1.download = iskName;
      a1.click();
      URL.revokeObjectURL(u1);
      const a2 = document.createElement("a");
      a2.href = u2;
      a2.download = calcName;
      a2.click();
      URL.revokeObjectURL(u2);
      pushNotice({
        kind: "success",
        title: "Документы сгенерированы",
        body: "Иск и расчёт к иску скачиваются в формате DOCX.",
      });
    } catch (e) {
      pushNotice({
        kind: "error",
        title: "Ошибка генерации",
        body: e instanceof Error ? e.message : String(e),
      });
    } finally {
      setGenBusy(false);
    }
  }, [companyType, endDateText, formState, packageId, pushNotice]);

  const pipelineIndex = useMemo(() => {
    const i = PIPELINE.findIndex((p) => p.key === packageState);
    return i >= 0 ? i : 0;
  }, [packageState]);

  const claimsText = formState.lawsuit_info.claims.join("\n");

  const calcBlocked = useMemo(() => {
    const f = formState;
    if (!f.court_info.addres.trim()) return true;
    if (!f.plaintiff_info.full_name.trim() || !f.plaintiff_info.inn.trim()) return true;
    if (!f.defendant_info.full_name.trim() || !f.defendant_info.inn.trim()) return true;
    if (!f.responsitive_name.trim()) return true;
    return false;
  }, [formState]);

  const toggleNotif = useCallback(() => {
    setNotifCollapsed((c) => !c);
  }, []);

  const layoutClass = notifCollapsed ? "layout layout--notif-collapsed" : "layout";
  const panelClass = notifCollapsed
    ? "panel notifications-panel notifications-panel--collapsed"
    : "panel notifications-panel";

  if (!authenticated) {
    return (
      <>
        <SvgSprite />
        <LoginScreen
          onLoggedIn={onLoggedIn}
        />
      </>
    );
  }

  return (
    <>
      <SvgSprite />
      <header className="app-header">
        <h1 className="app-title">LegalDocInspector</h1>
        <div className="app-header-meta">
          <span className="badge badge--extracting">
            <Icon id="i-user" />
            {userLabel}
          </span>
          {packageId ? (
            <span className="badge">packageId: {packageId}</span>
          ) : (
            <span className="badge">пакет не создан</span>
          )}
          <span className="badge badge--ok" title="Состояние пакета">
            <Icon id="i-check" />
            {packageState}
          </span>
          <button type="button" className="btn btn--secondary" onClick={onLogout}>
            Выйти
          </button>
        </div>
      </header>

      <div className={layoutClass}>
        <main className="stack">
          <section className="panel">
            <h2>2. Пакет и дата заявления</h2>
            <div className="form-grid form-grid--align-inputs">
              <div className="field">
                <label htmlFor="app-date">Дата составления заявления</label>
                <input
                  id="app-date"
                  type="date"
                  value={applicationDateIso}
                  onChange={(e) => setApplicationDateIso(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="end-date">Дата конца просрочки (расчёт)</label>
                <input
                  id="end-date"
                  type="text"
                  value={endDateText}
                  onChange={(e) => setEndDateText(e.target.value)}
                  placeholder="ДД.ММ.ГГГГ"
                />
              </div>
              <div className="field">
                <label htmlFor="co-type">Тип компании (УК / ТСЖ / Прочие)</label>
                <select
                  id="co-type"
                  value={companyType}
                  onChange={(e) => setCompanyType(e.target.value)}
                >
                  <option value="ТСЖ">ТСЖ</option>
                  <option value="УК">УК</option>
                  <option value="Прочие">Прочие</option>
                </select>
              </div>
            </div>
            <div className="pipeline" aria-label="Состояния пакета">
              {PIPELINE.map((step, idx) => {
                let cls = "pipeline-step";
                if (idx < pipelineIndex) cls += " pipeline-step--done";
                else if (idx === pipelineIndex) cls += " pipeline-step--active";
                return (
                  <span key={step.key} style={{ display: "contents" }}>
                    {idx > 0 ? <span className="pipeline-arrow">→</span> : null}
                    <span className={cls}>{step.label}</span>
                  </span>
                );
              })}
            </div>
          </section>

          <section className="panel">
            <h2>3. Загрузка документов</h2>
            <p className="hint-muted">
              Один пакет с клиента: ЕГРЮЛ PDF и комплекты (договор, претензия, справки Excel).
            </p>

            <p className="section-label">Выписка ЕГРЮЛ (PDF)</p>
            <div className="file-row file-row--empty">
              <Icon id="i-pdf" style={{ color: egrulFile ? "#c42b2b" : "var(--muted)" }} />
              <div className="file-row__meta">
                <strong>ЕГРЮЛ</strong>
                {egrulFile ? (
                  <> — {egrulFile.name}</>
                ) : (
                  <div className="file-row__empty-note">Файл не выбран</div>
                )}
              </div>
              <div className="file-row__actions">
                <input
                  id="egrul-input"
                  type="file"
                  accept=".pdf,application/pdf"
                  style={{ display: "none" }}
                  onChange={(e) => {
                    setEgrulFile(e.target.files?.[0] ?? null);
                    e.target.value = "";
                  }}
                />
                <button
                  type="button"
                  className="btn btn--secondary btn--compact"
                  onClick={() => document.getElementById("egrul-input")?.click()}
                >
                  Выбрать файл…
                </button>
                {egrulFile ? (
                  <button type="button" className="btn btn--secondary btn--compact" onClick={() => setEgrulFile(null)}>
                    Удалить
                  </button>
                ) : null}
              </div>
            </div>

            {complects.map((c, idx) => (
              <ComplectFiles
                key={c.id}
                index={idx}
                value={c}
                canRemove={complects.length > 1}
                onRemove={
                  complects.length > 1
                    ? () => setComplects((prev) => prev.filter((x) => x.id !== c.id))
                    : undefined
                }
                onChange={(next) =>
                  setComplects((prev) => prev.map((x) => (x.id === c.id ? next : x)))
                }
              />
            ))}

            <button
              type="button"
              className="btn btn--primary"
              style={{ marginTop: "0.75rem" }}
              disabled={complects.length >= 30}
              onClick={() => setComplects((p) => [...p, emptyComplect()])}
            >
              <Icon id="i-upload" />
              Добавить комплект
            </button>
            <button
              type="button"
              className="btn btn--primary"
              style={{ marginLeft: "0.5rem" }}
              disabled={extractBusy || polling}
              onClick={onRunExtract}
            >
              <Icon id="i-refresh" />
              {extractBusy || polling ? "Извлечение…" : "Запустить извлечение"}
            </button>
          </section>

          <section className="panel">
            <h2>4. Прогресс</h2>
            <div className="progress-meta">
              <span>
                <Icon id="i-spinner" /> Состояние: <strong>{packageState}</strong>
              </span>
              <span>
                {polling ? "Опрос статуса каждые 2 с…" : "Ожидание действий"}
              </span>
            </div>
            <div className="progress-line">
              <div
                className="progress-line__fill"
                style={{
                  width: packageState === "extracting" ? "45%" : packageState === "extracted" ? "100%" : "12%",
                }}
              />
            </div>
            <p className="hint-muted">
              По мере завершения извлечения форма в п. 6 заполняется данными с сервера (GET /form после статуса
              extracted).
            </p>
          </section>

          <section className="panel">
            <h2>5. Конфликты и поля по документам</h2>
            {Array.isArray(parseResult?.parse_warnings) && parseResult.parse_warnings.length > 0 ? (
              <div className="form-grid" style={{ marginBottom: "0.85rem" }}>
                <div className="field field--full">
                  <p className="section-label" style={{ marginBottom: "0.35rem" }}>
                    Предупреждения разбора (parse_warnings)
                  </p>
                  <ul className="parse-warnings-list" style={{ margin: 0, paddingLeft: "1.2rem" }}>
                    {(parseResult.parse_warnings as unknown[])
                      .filter((w): w is string => typeof w === "string" && w.trim().length > 0)
                      .map((w, idx) => (
                        <li key={`pw-${idx}`} className="hint-muted" style={{ marginBottom: "0.35rem" }}>
                          {w.trim()}
                        </li>
                      ))}
                  </ul>
                </div>
              </div>
            ) : null}
            {parseResult?.results_of_name_parser ? (
              <div className="form-grid">
                <div className="field field--full">
                  <label>Фрагмент разбора (results_of_name_parser)</label>
                  <textarea
                    readOnly
                    rows={6}
                    value={JSON.stringify(parseResult.results_of_name_parser, null, 2)}
                    className="hint-muted"
                    style={{ width: "100%", fontFamily: "monospace", fontSize: "0.78rem" }}
                  />
                </div>
              </div>
            ) : (
              <p className="hint-muted">После извлечения здесь появятся данные из разбора для сверки.</p>
            )}
          </section>

          <section className="panel">
            <h2>6. Форма (истец, ответчик, суд, иск)</h2>
            <p className="hint-muted">
              Поля обновляются из результата извлечения; правки отправляются на сервер перед расчётом и генерацией.
            </p>

            <h3>Суд</h3>
            <div className="form-grid">
              <div className="field field--full">
                <label>Название органа</label>
                <input
                  type="text"
                  value={formState.court_info.name}
                  onChange={(e) =>
                    setFormState((s) => ({
                      ...s,
                      court_info: { ...s.court_info, name: e.target.value },
                    }))
                  }
                />
              </div>
              <div className={`field field--full${!formState.court_info.addres.trim() ? " field--error" : ""}`}>
                <label>Адрес органа</label>
                <input
                  type="text"
                  value={formState.court_info.addres}
                  onChange={(e) =>
                    setFormState((s) => ({
                      ...s,
                      court_info: { ...s.court_info, addres: e.target.value },
                    }))
                  }
                  placeholder="обязательное поле"
                />
                {!formState.court_info.addres.trim() ? (
                  <div className="field-hint">
                    <Icon id="i-alert" /> Заполните поле для расчёта
                  </div>
                ) : null}
              </div>
            </div>

            <h3>Истец (plaintiff_info)</h3>
            <div className="form-grid">
              <div className="field field--full">
                <label>Полное наименование</label>
                <input
                  value={formState.plaintiff_info.full_name}
                  onChange={(e) =>
                    setFormState((s) => ({
                      ...s,
                      plaintiff_info: { ...s.plaintiff_info, full_name: e.target.value },
                    }))
                  }
                />
              </div>
              <div className="field">
                <label>Сокращённое наименование</label>
                <input
                  value={formState.plaintiff_info.short_name}
                  onChange={(e) =>
                    setFormState((s) => ({
                      ...s,
                      plaintiff_info: { ...s.plaintiff_info, short_name: e.target.value },
                    }))
                  }
                />
              </div>
              <div className="field">
                <label>ИНН</label>
                <input
                  value={formState.plaintiff_info.inn}
                  onChange={(e) =>
                    setFormState((s) => ({
                      ...s,
                      plaintiff_info: { ...s.plaintiff_info, inn: e.target.value },
                    }))
                  }
                />
              </div>
              <div className="field">
                <label>ОГРН</label>
                <input
                  value={formState.plaintiff_info.ogrn}
                  onChange={(e) =>
                    setFormState((s) => ({
                      ...s,
                      plaintiff_info: { ...s.plaintiff_info, ogrn: e.target.value },
                    }))
                  }
                />
              </div>
              <div className="field field--full">
                <label>Адрес (addres)</label>
                <input
                  value={formState.plaintiff_info.addres}
                  onChange={(e) =>
                    setFormState((s) => ({
                      ...s,
                      plaintiff_info: { ...s.plaintiff_info, addres: e.target.value },
                    }))
                  }
                />
              </div>
              <div className="field field--full">
                <label>Адрес для корреспонденции</label>
                <input
                  value={formState.plaintiff_info.correspondency_addres}
                  onChange={(e) =>
                    setFormState((s) => ({
                      ...s,
                      plaintiff_info: { ...s.plaintiff_info, correspondency_addres: e.target.value },
                    }))
                  }
                />
              </div>
            </div>

            <h3>Ответчик (defendant_info)</h3>
            <div className="form-grid">
              <div className="field field--full">
                <label>Полное наименование</label>
                <input
                  value={formState.defendant_info.full_name}
                  onChange={(e) =>
                    setFormState((s) => ({
                      ...s,
                      defendant_info: { ...s.defendant_info, full_name: e.target.value },
                    }))
                  }
                />
              </div>
              <div className="field">
                <label>Сокращённое наименование</label>
                <input
                  value={formState.defendant_info.short_name}
                  onChange={(e) =>
                    setFormState((s) => ({
                      ...s,
                      defendant_info: { ...s.defendant_info, short_name: e.target.value },
                    }))
                  }
                />
              </div>
              <div className="field">
                <label>ИНН</label>
                <input
                  value={formState.defendant_info.inn}
                  onChange={(e) =>
                    setFormState((s) => ({
                      ...s,
                      defendant_info: { ...s.defendant_info, inn: e.target.value },
                    }))
                  }
                />
              </div>
              <div className="field">
                <label>ОГРН</label>
                <input
                  value={formState.defendant_info.ogrn}
                  onChange={(e) =>
                    setFormState((s) => ({
                      ...s,
                      defendant_info: { ...s.defendant_info, ogrn: e.target.value },
                    }))
                  }
                />
              </div>
              <div className="field field--full">
                <label>Адрес</label>
                <input
                  value={formState.defendant_info.addres}
                  onChange={(e) =>
                    setFormState((s) => ({
                      ...s,
                      defendant_info: { ...s.defendant_info, addres: e.target.value },
                    }))
                  }
                />
              </div>
            </div>

            {Object.keys(formState.complects).length > 0 ? (
              <>
                <h3>По договорам (комплекты)</h3>
                {Object.entries(formState.complects).map(([cn, row]) => (
                  <div key={cn} className="lawsuit-docset-calc-block">
                    <h4 className="lawsuit-docset-calc-block__title">Договор {cn}</h4>
                    <div className="form-grid">
                      <div className="field">
                        <label>Тип договора</label>
                        <select
                          value={row.contract_type}
                          onChange={(e) =>
                            setFormState((s) => ({
                              ...s,
                              complects: {
                                ...s.complects,
                                [cn]: { ...row, contract_type: e.target.value },
                              },
                            }))
                          }
                        >
                          <option>ТЭ</option>
                          <option>ГВС</option>
                          <option>СОИ</option>
                          <option>ФОТЭ</option>
                        </select>
                      </div>
                      <div className="field">
                        <label>День оплаты (day_of_penalty)</label>
                        <input
                          type="text"
                          value={row.day_of_penalty}
                          onChange={(e) =>
                            setFormState((s) => ({
                              ...s,
                              complects: {
                                ...s.complects,
                                [cn]: { ...row, day_of_penalty: e.target.value },
                              },
                            }))
                          }
                          placeholder="число месяца"
                        />
                      </div>
                      <div className="field">
                        <label>Пункт договора (contract_point)</label>
                        <input
                          value={row.contract_point}
                          onChange={(e) =>
                            setFormState((s) => ({
                              ...s,
                              complects: {
                                ...s.complects,
                                [cn]: { ...row, contract_point: e.target.value },
                              },
                            }))
                          }
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </>
            ) : null}

            <div className="lawsuit-calc-toolbar">
              <button
                type="button"
                className="btn btn--primary"
                disabled={calcBusy || !packageId || calcBlocked}
                onClick={onCalculateOnly}
              >
                <Icon id="i-check" />
                {calcBusy ? "Расчёт…" : "Произвести расчёт"}
              </button>
              <span className="hint-muted">
                {calcBlocked
                  ? "Заполните обязательные поля (суд, истец, ответчик, ФИО ответственного)."
                  : "Отправляет текущую форму и запускает расчёт на сервере."}
              </span>
            </div>

            <h3>Иск (lawsuit_info)</h3>
            <div className="form-grid">
              <div className="field">
                <label>Цена иска</label>
                <input
                  value={formState.lawsuit_info.cost}
                  onChange={(e) =>
                    setFormState((s) => ({
                      ...s,
                      lawsuit_info: { ...s.lawsuit_info, cost: e.target.value },
                    }))
                  }
                />
              </div>
              <div className="field">
                <label>Госпошлина</label>
                <input
                  value={formState.lawsuit_info.tax}
                  onChange={(e) =>
                    setFormState((s) => ({
                      ...s,
                      lawsuit_info: { ...s.lawsuit_info, tax: e.target.value },
                    }))
                  }
                />
              </div>
              <div className="field field--full">
                <label>Претензии (по строкам)</label>
                <textarea
                  rows={3}
                  value={claimsText}
                  onChange={(e) =>
                    setFormState((s) => ({
                      ...s,
                      lawsuit_info: {
                        ...s.lawsuit_info,
                        claims: e.target.value
                          .split("\n")
                          .map((x) => x.trim())
                          .filter(Boolean),
                      },
                    }))
                  }
                  placeholder="Каждая претензия с новой строки"
                />
              </div>
              <div className={`field field--full${!formState.responsitive_name.trim() ? " field--error" : ""}`}>
                <label>ФИО ответственного (responsitive_name)</label>
                <input
                  value={formState.responsitive_name}
                  onChange={(e) => setFormState((s) => ({ ...s, responsitive_name: e.target.value }))}
                  placeholder="обязательно"
                />
                {!formState.responsitive_name.trim() ? (
                  <div className="field-hint">
                    <Icon id="i-alert" /> Заполните поле
                  </div>
                ) : null}
              </div>
            </div>

            <div className="toolbar toolbar--after-docset-calcs">
              <button
                type="button"
                className="btn btn--primary"
                disabled={genBusy || !packageId || calcBlocked}
                onClick={onGenerateDocs}
              >
                <Icon id="i-download" />
                {genBusy ? "Генерация…" : "Сгенерировать иск и расчёт к иску"}
              </button>
            </div>
          </section>
        </main>

        <aside
          className={panelClass}
          id="backend-notifications-panel"
          aria-label="Панель уведомлений от бэкенда"
        >
          <div className="notifications-panel__header">
            <h2 className="notifications-panel__title" id="backend-notifications-heading">
              Уведомления бэкенда
            </h2>
            <button
              type="button"
              className="btn btn--icon notifications-panel__toggle"
              aria-expanded={!notifCollapsed}
              aria-controls="backend-notifications-body"
              title={notifCollapsed ? "Развернуть панель" : "Свернуть панель"}
              onClick={toggleNotif}
            >
              <Icon
                id="i-chevron-right"
                className="icon icon-lg notifications-panel__toggle-icon"
              />
              <span className="visually-hidden">
                {notifCollapsed ? "Развернуть панель уведомлений" : "Свернуть панель уведомлений"}
              </span>
            </button>
          </div>

          <div
            className="notifications-panel__body"
            id="backend-notifications-body"
            role="region"
            aria-labelledby="backend-notifications-heading"
          >
            {notices.length === 0 ? (
              <p className="hint-muted" style={{ marginTop: 0 }}>
                Здесь появляются сообщения о запросах к API и статусах обработки.
              </p>
            ) : (
              notices.map((n) => (
                <div key={n.id} className={`notice notice--${n.kind === "success" ? "success" : n.kind === "error" ? "error" : n.kind === "warning" ? "warning" : "info"}`}>
                  <Icon
                    id={
                      n.kind === "success"
                        ? "i-check"
                        : n.kind === "error"
                          ? "i-error"
                          : n.kind === "warning"
                            ? "i-alert"
                            : "i-info"
                    }
                    className="icon icon-lg"
                  />
                  <div className="notice__body">
                    <div className="notice__title">{n.title}</div>
                    {n.body}
                    {n.code ? <div className="notice__code">{n.code}</div> : null}
                  </div>
                </div>
              ))
            )}
          </div>
        </aside>
      </div>

      <div className="toast-stack" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast--${t.kind}`} role="status">
            <div className="toast__body">
              <strong>{t.title}</strong>
              <br />
              {t.body}
            </div>
            <button
              type="button"
              className="toast__close"
              aria-label="Закрыть уведомление"
              title="Закрыть"
              onClick={() => dismissToast(t.id)}
            >
              <Icon id="i-close" />
            </button>
          </div>
        ))}
      </div>
    </>
  );
}
