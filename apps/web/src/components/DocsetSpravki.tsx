import { useCallback, useMemo, useRef, useState } from "react";
import { Icon } from "./SvgSprite";

const SPRAVKI_MAX_PER_DOCSET = 20;

export type SpravkaInitialRow =
  | { kind: "empty" }
  | {
      kind: "loaded";
      filename: string;
      badge: "ok" | "partial";
      /** true — текст provenance как в tpl-spravka-row-loaded после выбора файла */
      fromPick?: boolean;
    };

type SprRow =
  | { id: string; kind: "empty" }
  | {
      id: string;
      kind: "loaded";
      filename: string;
      badge: "ok" | "partial";
      fromPick?: boolean;
    };

function newId() {
  return crypto.randomUUID();
}

export function DocsetSpravki({
  initialRows,
  hintText,
}: {
  initialRows: SpravkaInitialRow[];
  hintText: string;
}) {
  const [rows, setRows] = useState<SprRow[]>(() =>
    initialRows.map((r) =>
      r.kind === "empty"
        ? { id: newId(), kind: "empty" }
        : {
            id: newId(),
            kind: "loaded",
            filename: r.filename,
            badge: r.badge,
            fromPick: r.fromPick,
          }
    )
  );

  const fileInputRef = useRef<HTMLInputElement>(null);
  const pickTargetIdRef = useRef<string | null>(null);

  const atLimit = rows.length >= SPRAVKI_MAX_PER_DOCSET;

  const onPickFile = useCallback(() => {
    const id = pickTargetIdRef.current;
    pickTargetIdRef.current = null;
    const f = fileInputRef.current?.files?.[0];
    if (!id || !f) {
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }
    setRows((prev) =>
      prev.map((row) =>
        row.id === id
          ? {
              id: row.id,
              kind: "loaded",
              filename: f.name,
              badge: "ok",
              fromPick: true,
            }
          : row
      )
    );
    if (fileInputRef.current) fileInputRef.current.value = "";
  }, []);

  const addRow = useCallback(() => {
    if (rows.length >= SPRAVKI_MAX_PER_DOCSET) return;
    setRows((prev) => [...prev, { id: newId(), kind: "empty" }]);
  }, [rows.length]);

  const removeSlot = useCallback((rowId: string) => {
    setRows((prev) => {
      if (prev.length <= 1) return prev;
      return prev.filter((r) => r.id !== rowId);
    });
  }, []);

  const deleteFile = useCallback((rowId: string) => {
    setRows((prev) =>
      prev.map((r) =>
        r.id === rowId ? { id: r.id, kind: "empty" as const } : r
      )
    );
  }, []);

  const openPick = useCallback((rowId: string) => {
    pickTargetIdRef.current = rowId;
    fileInputRef.current?.click();
  }, []);

  const removeSlotVisible = useMemo(() => rows.length > 1, [rows.length]);

  return (
    <div className="docset-spravki">
      <input
        ref={fileInputRef}
        type="file"
        accept=".xls,.xlsx,.xlsm"
        aria-hidden="true"
        style={{
          position: "fixed",
          left: "-9999px",
          opacity: 0,
          pointerEvents: "none",
        }}
        onChange={onPickFile}
      />
      <div className="docset-spravki__toolbar">
        <span className="docset-spravki__title">Справки о задолженности</span>
        <button
          type="button"
          className="btn btn--secondary btn--compact js-add-spravka"
          disabled={atLimit}
          aria-disabled={atLimit ? "true" : "false"}
          onClick={(e) => {
            e.preventDefault();
            addRow();
          }}
        >
          Добавить справку
        </button>
      </div>
      <div className="docset-spravki__list">
        {rows.map((row, idx) => {
          const title = `Справка ${idx + 1}`;
          if (row.kind === "empty") {
            return (
              <div
                key={row.id}
                className="file-row file-row--empty file-row--spravka"
              >
                <Icon id="i-xls" style={{ color: "var(--muted)" }} />
                <div className="file-row__meta">
                  <strong>
                    <span className="spravka-slot-title">{title}</span>
                  </strong>{" "}
                  (.xls / .xlsx / .xlsm)
                  <div className="file-row__empty-note">Файл не загружен</div>
                </div>
                <div className="file-row__actions file-row__actions--spravka-empty">
                  <button
                    type="button"
                    className="btn btn--secondary btn--compact js-spravka-pick"
                    onClick={(e) => {
                      e.preventDefault();
                      openPick(row.id);
                    }}
                  >
                    Выбрать файл…
                  </button>
                  <button
                    type="button"
                    className="btn btn--secondary btn--compact js-spravka-remove-slot"
                    hidden={!removeSlotVisible}
                    onClick={(e) => {
                      e.preventDefault();
                      removeSlot(row.id);
                    }}
                  >
                    Удалить справку
                  </button>
                </div>
              </div>
            );
          }

          const prov = row.fromPick
            ? "extractionMethod: excelParser (TableParser) · макет"
            : "extractionMethod: excelParser (TableParser)";

          return (
            <div key={row.id} className="file-row file-row--spravka">
              <Icon id="i-xls" style={{ color: "#1d7a4c" }} />
              <div className="file-row__meta">
                <strong>
                  <span className="spravka-slot-title">{title}</span>
                </strong>{" "}
                — <span className="spravka-filename">{row.filename}</span>
                <div className="provenance">{prov}</div>
              </div>
              <div className="file-row__actions">
                {row.badge === "ok" ? (
                  <span className="badge badge--ok">
                    <Icon id="i-check" />
                  </span>
                ) : (
                  <span className="badge badge--partial">partial</span>
                )}
                <button
                  type="button"
                  className="btn btn--secondary btn--compact js-spravka-delete-file"
                  onClick={(e) => {
                    e.preventDefault();
                    deleteFile(row.id);
                  }}
                >
                  <Icon id="i-trash" /> Удалить файл
                </button>
                <button
                  type="button"
                  className="btn btn--secondary btn--compact js-spravka-remove-slot"
                  hidden={!removeSlotVisible}
                  onClick={(e) => {
                    e.preventDefault();
                    removeSlot(row.id);
                  }}
                >
                  Удалить справку
                </button>
              </div>
            </div>
          );
        })}
      </div>
      <p className="hint-muted docset-spravki__hint">{hintText}</p>
    </div>
  );
}
