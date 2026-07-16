import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        base: {
          bg: "#0B0C0E",
          panel: "#131417",
          card: "#17181C",
          line: "#2C2D31"
        },
        signal: {
          go: "#8FBF9F",
          goDim: "#1C2620",
          warn: "#D9A441",
          warnDim: "#2A2419",
          stop: "#C4685C",
          stopDim: "#2A1E1B"
        },
        ink: {
          primary: "#EDEDEF",
          secondary: "#98999E",
          muted: "#5C5D63"
        }
      },
      fontFamily: {
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
        sans: ["IBM Plex Sans", "ui-sans-serif", "system-ui", "sans-serif"]
      },
      borderRadius: {
        none: "0px",
        sm: "2px",
        DEFAULT: "3px"
      },
      letterSpacing: {
        tightish: "-0.01em",
        wideish: "0.06em"
      }
    }
  },
  plugins: []
};

export default config;
