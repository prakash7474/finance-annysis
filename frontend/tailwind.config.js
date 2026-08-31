/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0B0F16",
        panel: "#10151D",
        "panel-raised": "#161D28",
        card: "#0F141C",
        card2: "#161D28",
        border: "#232B3A",
        "border-soft": "#1B2230",
        green: "#22C55E",
        "green-dim": "#16803B",
        amber: "#F59E0B",
        red: "#EF4444",
        "red-dim": "#B91C1C",
        blue: "#3B82F6",
        violet: "#8B5CF6",
        text: "#F1F5F9",
        text2: "#9AA7B8",
        muted: "#6B7688",
      },
      fontFamily: {
        display: ['"Space Grotesk"', '"Inter"', "sans-serif"],
        sans: ['"Inter"', "-apple-system", '"Segoe UI"', "Roboto", "sans-serif"],
        mono: ['"IBM Plex Mono"', '"JetBrains Mono"', "ui-monospace", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(0,0,0,0.3), 0 8px 24px -12px rgba(0,0,0,0.35)",
        "card-hover": "0 2px 4px rgba(0,0,0,0.3), 0 12px 32px -12px rgba(0,0,0,0.4)",
        panel: "0 1px 0 rgba(255,255,255,0.03) inset",
      },
      keyframes: {
        priceFlashGreen: {
          "0%": { color: "#3DDC97", textShadow: "0 0 8px rgba(61,220,151,0.4)" },
          "100%": { color: "#E8EAED", textShadow: "none" },
        },
        priceFlashRed: {
          "0%": { color: "#E85D5D", textShadow: "0 0 8px rgba(232,93,93,0.4)" },
          "100%": { color: "#E8EAED", textShadow: "none" },
        },
        ruleOverridePulse: {
          "0%": { transform: "scale(1)", boxShadow: "0 0 0 0 rgba(217,164,65,0.4)" },
          "50%": { transform: "scale(1.03)", boxShadow: "0 0 20px 4px rgba(217,164,65,0.3)" },
          "100%": { transform: "scale(1)", boxShadow: "0 0 0 0 rgba(217,164,65,0.0)" },
        },
        rowInsert: {
          "0%": { opacity: "0", transform: "translateY(-8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        stageReveal: {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pulseBar: {
          "0%, 100%": { height: "2px" },
          "50%": { height: "100%" },
        },
      },
      animation: {
        "price-flash-green": "priceFlashGreen 0.8s ease-out",
        "price-flash-red": "priceFlashRed 0.8s ease-out",
        "rule-pulse": "ruleOverridePulse 0.6s ease-out",
        "row-insert": "rowInsert 0.3s ease-out",
        "stage-reveal": "stageReveal 0.25s ease-out",
        "pulse-bar": "pulseBar 1.5s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
