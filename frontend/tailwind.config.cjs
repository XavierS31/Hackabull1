/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        panel: "#0f172a",
        surface: "#1e293b",
        accent: "#22c55e",
        warn: "#f97316"
      }
    }
  },
  plugins: []
};
