/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        troy: {
          red: "#9b2428",
          dark: "#7E1B2B",
          white: "#FFFFFF",
          gray: "#F5F5F5",
          ink: "#F1EFEA",
          surface: "#1F221C",
          clinic: "#171915",
          sage: "#86A094",
          line: "#35392F",
          amber: "#D9A354",
        },
      },
      fontFamily: {
        display: ["'Zilla Slab'", "serif"],
        mono: ["'IBM Plex Mono'", "monospace"],
      },
    },
  },
  plugins: [],
};
