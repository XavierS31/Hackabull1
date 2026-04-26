/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // Healthcare cyan-blue tech palette
        bg:       "#04121b",   // page background
        panel:    "#0a1f2c",   // card background
        surface:  "#0f2a3a",   // input/sub-surface
        border:   "#164a5f",   // hairline borders
        accent:   "#22d3ee",   // primary cyan
        accent2:  "#0891b2",   // deeper cyan
        good:     "#10b981",   // healthy green
        warn:     "#f59e0b",
        bad:      "#ef4444",
        ink:      "#e0f2fe",   // primary text (cool white)
        muted:    "#7dd3fc99"  // muted cyan-tinted text
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(34,211,238,0.25), 0 0 24px -8px rgba(34,211,238,0.45)"
      }
    }
  },
  plugins: []
};
