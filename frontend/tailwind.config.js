/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0B0E14",
        panel: "#12161F",
        "panel-raised": "#181D29",
        card: "#12161F",
        card2: "#181D29",
        border: "#1E2433",
        green: "#3DDC97",
        "green-dim": "#2B9E6F",
        amber: "#D9A441",
        red: "#E85D5D",
        "red-dim": "#B84848",
        blue: "#5B8DEF",
        text: "#E8EAED",
        text2: "#7A8194",
        muted: "#555E72",
      },
      fontFamily: {
        display: ['"Space Grotesk"', '"Inter"', "sans-serif"],
        sans: ['"Inter"', "-apple-system", '"Segoe UI"', "Roboto", "sans-serif"],
        mono: ['"IBM Plex Mono"', '"JetBrains Mono"', "ui-monospace", "monospace"],
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
