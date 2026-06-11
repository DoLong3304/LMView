import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";
import { defineConfig as defineVitestConfig } from "vitest/config";

export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "./src"),
        },
    },
    envDir: "../",
    server: {
        port: 3000,
        proxy: {
            "/api": {
                target: "http://localhost:8080",
                changeOrigin: true,
                ws: true,
            },
        },
    },
    build: {
        outDir: "dist",
        sourcemap: false,
        rollupOptions: {
            output: {
                manualChunks(id) {
                    if (!id.includes("node_modules")) return undefined;
                    const normalizedId = id.replace(/\\/g, "/");
                    if (
                        normalizedId.includes("/node_modules/react/") ||
                        normalizedId.includes("/node_modules/react-dom/") ||
                        normalizedId.includes("/node_modules/scheduler/")
                    ) {
                        return "vendor-react";
                    }
                    if (
                        normalizedId.includes(
                            "/node_modules/lightweight-charts/",
                        )
                    )
                        return "vendor-charts";
                    if (normalizedId.includes("/node_modules/lucide-react/"))
                        return "vendor-icons";
                    if (
                        normalizedId.includes(
                            "/node_modules/react-markdown/",
                        ) ||
                        normalizedId.includes("/node_modules/remark-") ||
                        normalizedId.includes("/node_modules/rehype-") ||
                        normalizedId.includes("/node_modules/micromark") ||
                        normalizedId.includes("/node_modules/mdast") ||
                        normalizedId.includes("/node_modules/hast") ||
                        normalizedId.includes("/node_modules/unified/") ||
                        normalizedId.includes("/node_modules/vfile") ||
                        normalizedId.includes("/node_modules/unist") ||
                        normalizedId.includes(
                            "/node_modules/property-information/",
                        ) ||
                        normalizedId.includes(
                            "/node_modules/space-separated-tokens/",
                        ) ||
                        normalizedId.includes(
                            "/node_modules/comma-separated-tokens/",
                        ) ||
                        normalizedId.includes(
                            "/node_modules/decode-named-character-reference/",
                        ) ||
                        normalizedId.includes(
                            "/node_modules/character-entities",
                        ) ||
                        normalizedId.includes(
                            "/node_modules/stringify-entities/",
                        )
                    ) {
                        return "vendor-markdown";
                    }
                    return undefined;
                },
            },
        },
    },
    test: {
        globals: true,
        environment: "jsdom",
        include: ["src/**/*.{test,spec}.{ts,tsx}"],
    },
});
