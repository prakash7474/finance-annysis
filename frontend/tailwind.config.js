/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0B0F14",
        panel: "#11161D",
        card: "#151B23",
        card2: "#1A212B",
        border: "#242B35",
        green: "#19C37D",
        amber: "#F5B942",
        red: "#EF5B67",
        blue: "#5B8DEF",
        text: "#F5F7FA",
        text2: "#9AA4B2",
        muted: "#687282",
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
      },
    },
  },
  plugins: [],
};
