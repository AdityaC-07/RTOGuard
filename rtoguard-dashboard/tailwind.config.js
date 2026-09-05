module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        beige:   { DEFAULT: '#FAF9F6', alt: '#F0EDE6' },
        navy:    { DEFAULT: '#1A3C6E', light: '#2B5499', subtle: '#E8EEF7' },
        ink:     { DEFAULT: '#0D0D0D', muted: '#3D3D3D' },
        border:  '#D9D4CB',
        safe:    { DEFAULT: '#1A3C6E', bg: '#E8EEF7' },
        caution: { DEFAULT: '#7A5C00', bg: '#FDF5DC' },
        risk:    { DEFAULT: '#5C1A1A', bg: '#FAEAEA' },
      },
      fontFamily: {
        'sans': ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
