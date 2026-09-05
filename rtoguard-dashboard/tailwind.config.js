module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        beige:   { DEFAULT: '#FFFFFF', alt: '#FFFFFF' },
        navy:    { DEFAULT: '#1A3C6E', light: '#2B5499', subtle: '#E8EEF7' },
        ink:     { DEFAULT: '#000000', muted: '#000000' },
        border:  '#1A3C6E',
        safe:    { DEFAULT: '#1A3C6E', bg: '#E8EEF7' },
        caution: { DEFAULT: '#1A3C6E', bg: '#FFFFFF' },
        risk:    { DEFAULT: '#000000', bg: '#FFFFFF' },
      },
      fontFamily: {
        'sans': ['Georgia', 'Times New Roman', 'serif'],
      },
    },
  },
  plugins: [],
}
