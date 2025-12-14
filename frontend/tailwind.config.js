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
        },
      },
      backgroundImage: {
        "troy-bg": "url('/src/assets/troycampus.png)",
      },
    },
  },
  plugins: [],
};
