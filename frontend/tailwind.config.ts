import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0a0a0a",
        surface: "#111111",
        accent: "#00ff88",
        "accent-dim": "#00cc6e",
        muted: "#666666",
        border: "#222222",
      },
      fontFamily: {
        mono: ["var(--font-mono)", "monospace"],
        display: ["var(--font-display)", "sans-serif"],
        sans: ["var(--font-display)", "sans-serif"],
      },
      animation: {
        "progress-fill": "progress-fill 0.5s ease-in-out",
      },
      keyframes: {
        "progress-fill": {
          from: { width: "0%" },
          to: { width: "var(--progress-width)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
