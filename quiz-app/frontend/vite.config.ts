import { defineConfig } from "vite";

// Dev server proxies API calls to the FastAPI backend (uvicorn on :8000),
// so `npm run dev` + `uvicorn app.main:app` gives live-reload development.
// The production build is plain static files served by Vercel (or by
// FastAPI itself from frontend/dist when running locally without Vite).
export default defineConfig({
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
  build: {
    outDir: "dist",
  },
});
