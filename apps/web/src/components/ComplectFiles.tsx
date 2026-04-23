import { useCallback, useId } from "react";
import { Icon } from "./SvgSprite";

export type ComplectFileState = {
  id: string;
  contract: File | null;
  preClaim: File | null;
  /** Слоты справок: null — пустой слот, File — выбранный файл */
  certificates: (File | null)[];
};

const MAX_CERTS = 20;

function newId() {
  return crypto.randomUUID();
}

export function emptyComplect(): ComplectFileState {
  return { id: newId(), contract: null, preClaim: null, certificates: [] };
}

type Props = {
  index: number;
  value: ComplectFileState;
  onChange: (next: ComplectFileState) => void;
  onRemove?: () => void;
  canRemove: boolean;
};

export function ComplectFiles({ index, value, onChange, onRemove, canRemove }: Props) {
  const base = useId().replace(/:/g, "");

  const setCert = useCallback(
    (slot: number, file: File | null) => {
      const certs = [...value.certificates];
      if (file) {
        while (certs.length <= slot) certs.push(null);
        certs[slot] = file;
        onChange({ ...value, certificates: certs });
      } else {
        certs.splice(slot, 1);
        onChange({ ...value, certificates: certs });
      }
    },
    [onChange, value]
  );

  const addCertSlot = useCallback(() => {
    if (value.certificates.length >= MAX_CERTS) return;
    onChange({ ...value, certificates: [...value.certificates, null] });
  }, [onChange, value]);

  return (
    <div className="docset">
      <div className="docset-header">
        <span className="docset-title">Комплект {index + 1}</span>
        {canRemove && onRemove ? (
          <button type="button" className="btn btn--secondary" onClick={onRemove}>
            <Icon id="i-trash" /> Удалить комплект
          </button>
        ) : null}
      </div>

      <FileRow
        label="Договор"
        sub="PDF"
        file={value.contract}
        inputId={`${base}-c`}
        accept=".pdf,application/pdf"
        onPick={(f) => onChange({ ...value, contract: f })}
        onClear={() => onChange({ ...value, contract: null })}
      />
      <FileRow
        label="Претензия"
        sub="PDF"
        file={value.preClaim}
        inputId={`${base}-p`}
        accept=".pdf,application/pdf"
        onPick={(f) => onChange({ ...value, preClaim: f })}
        onClear={() => onChange({ ...value, preClaim: null })}
      />

      <p className="section-label" style={{ marginTop: "0.75rem" }}>
        Справки о задолженности (Excel, до {MAX_CERTS} файлов, минимум 1 файл на комплект)
      </p>
      {value.certificates.map((file, j) => (
        <FileRow
          key={`${value.id}-cert-${j}`}
          label={`Справка ${j + 1}`}
          sub=".xls / .xlsx / .xlsm"
          file={file}
          inputId={`${base}-cert-${j}`}
          accept=".xls,.xlsx,.xlsm"
          onPick={(f) => setCert(j, f)}
          onClear={() => setCert(j, null)}
        />
      ))}
      <button
        type="button"
        className="btn btn--secondary"
        style={{ marginTop: "0.35rem" }}
        disabled={value.certificates.length >= MAX_CERTS}
        onClick={addCertSlot}
      >
        Добавить слот справки
      </button>
    </div>
  );
}

function FileRow(props: {
  label: string;
  sub: string;
  file: File | null;
  inputId: string;
  accept: string;
  onPick: (f: File | null) => void;
  onClear?: () => void;
}) {
  const { label, sub, file, inputId, accept, onPick, onClear } = props;
  const isPdf = sub.includes("PDF");
  return (
    <div className={`file-row ${file ? "" : "file-row--empty"}`}>
      <Icon
        id={isPdf ? "i-pdf" : "i-xls"}
        style={{ color: file ? (isPdf ? "#c42b2b" : "#1d7a4c") : "var(--muted)" }}
      />
      <div className="file-row__meta">
        <strong>{label}</strong> — {sub}
        {file ? (
          <>
            {" "}
            — <span className="spravka-filename">{file.name}</span>
          </>
        ) : (
          <div className="file-row__empty-note">Файл не загружен</div>
        )}
      </div>
      <div className="file-row__actions">
        <input
          id={inputId}
          type="file"
          accept={accept}
          style={{ display: "none" }}
          onChange={(e) => {
            const f = e.target.files?.[0] ?? null;
            onPick(f);
            e.target.value = "";
          }}
        />
        <button
          type="button"
          className="btn btn--secondary btn--compact"
          onClick={() => document.getElementById(inputId)?.click()}
        >
          Выбрать файл…
        </button>
        {file && onClear ? (
          <button type="button" className="btn btn--secondary btn--compact" onClick={onClear}>
            <Icon id="i-trash" /> Удалить
          </button>
        ) : null}
      </div>
    </div>
  );
}
