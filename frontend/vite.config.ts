/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dev server proxies /api and /health to the Python backend so the browser
// talks to one origin. Set BACKEND_URL if the backend runs elsewhere, or
// VITE_API_BASE to make the browser call a backend directly (no proxy).
const backend = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/api": backend,
      "/health": backend,
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    globals: false,
    // The default "forks" pool (and often "threads") hit the worker start
    // timeout on this Windows machine (observed 6 Oct 2026, Node 24.12);
    // vmThreads starts reliably. jsdom + user-event are slow here, so allow
    // generous per-test time.
    pool: "vmThreads",
    testTimeout: 30_000,
    hookTimeout: 30_000,
  },
});
