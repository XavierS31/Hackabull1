export default function CameraPanel({ src }) {
  return (
    <div className="relative overflow-hidden rounded border border-slate-800 bg-black">
      <img
        src={src}
        alt="Live stream frame"
        className="h-[240px] w-full object-cover"
        onError={(e) => {
          e.currentTarget.style.opacity = "0.25";
        }}
      />
    </div>
  );
}
