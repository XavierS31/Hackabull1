const EMPTY = "Not available";

export default function PatientProfile({ patient }) {
  if (!patient || Object.keys(patient).length === 0) {
    return <p className="text-sm text-slate-400">Upload onboarding QR to populate patient profile.</p>;
  }

  return (
    <div className="space-y-2 text-sm">
      <Row label="Name" value={patient.name} />
      <Row label="DOB" value={patient.dob} />
      <Row label="Emergency" value={patient.emergency_contact} />
      <Row label="Conditions" value={(patient.conditions || []).join(", ")} />
      <Row label="Allergies" value={(patient.allergies || []).join(", ")} />
      <Row label="Medications" value={(patient.medications || []).join(", ")} />
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="grid grid-cols-[100px_1fr] gap-2 border-b border-slate-800 py-1">
      <span className="text-slate-400">{label}</span>
      <span className="text-slate-100">{value || EMPTY}</span>
    </div>
  );
}
