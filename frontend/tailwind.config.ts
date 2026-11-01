import type { Config } from "tailwindcss";
const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: { extend: { colors: { luna: { black: "#050705", panel: "#0D110D", green: "#7CFC00", muted: "#8B9488" } } } },
  plugins: [],
};
export default config;
