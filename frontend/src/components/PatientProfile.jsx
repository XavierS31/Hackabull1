import { QrCode, Upload } from "lucide-react";
import { useRef, useState } from "react";

const EMPTY = "—";

export default function PatientProfile({ patient, onPatientUpdate }) {
  const fileRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const upload = async (file) => {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      const resp = await fetch("/api/onboarding/qr", { method: "POST", body: fd });
      const data = await resp.json();
      if (!resp.ok) {
        setError(data.detail || "QR parse failed.");
        return;
      }
      if (data.patient_profile && onPatientUpdate) {
        onPatientUpdate(data.patient_profile);
      }
    } catch (e) {
      setError("Network error: " + e.message);
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const hasPatient = patient && Object.keys(patient).length > 0;

  return (
    <div className="flex items-center gap-3">
      <div className="flex h-9 w-9 items-center justify-center rounded-full border border-border bg-surface">
        <QrCode size={16} className="text-accent" />
      </div>

      <div className="min-w-0 flex-1">
        {hasPatient ? (
          <>
            <p className="truncate text-sm font-semibold text-ink">
              {patient.name || "Unnamed Patient"}
            </p>
            <p className="truncate text-[11px] text-muted">
              {[patient.dob, (patient.conditions || []).join(", ") || "no conditions"]
                .filter(Boolean)
                .join(" · ") || EMPTY}
            </p>
          </>
        ) : (
          <>
            <p className="text-sm font-semibold text-ink">No patient loaded</p>
            <p className="text-[11px] text-muted">Upload onboarding QR to populate profile.</p>
          </>
        )}
        {error && <p className="mt-0.5 text-[11px] text-bad">{error}</p>}
      </div>

      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => upload(e.target.files?.[0])}
      />
      <button
        onClick={() => fileRef.current?.click()}
        disabled={busy}
        className="flex items-center gap-1.5 rounded-md border border-border bg-surface px-3 py-1.5 text-xs font-semibold text-accent hover:border-accent hover:shadow-glow disabled:opacity-50"
        title="Upload an onboarding QR image"
      >
        <Upload size={12} />
        {busy ? "Parsing…" : "QR"}
      </button>
    </div>
  );
}
