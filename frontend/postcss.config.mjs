// postcss-import primeiro: junta componentes.css ao globals.css para o Tailwind pôr as classes wl- em @layer components.
const config = { plugins: { "postcss-import": {}, tailwindcss: {}, autoprefixer: {} } };

export default config;
