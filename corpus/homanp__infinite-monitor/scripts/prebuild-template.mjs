/**
 * Pre-builds the widget base template (npm install + shadcn components)
 * so it is ready at server start instead of being installed on first request.
 *
 * Run automatically via the "postbuild" npm script.
 */

import { execSync } from "node:child_process";
import { writeFileSync, mkdirSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";

const BASE_DIR = join(process.cwd(), ".cache", "widget-base-template");

const TEMPLATES = {
  "index.html": `<!DOCTYPE html>\n<html lang="en" class="dark">\n  <head><meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" /><title>Widget</title></head>\n  <body style="margin:0; background:transparent;"><div id="root"></div><script type="module" src="/src/main.tsx"></script></body>\n</html>`,

  "src/main.tsx": `import React from "react";\nimport { createRoot } from "react-dom/client";\nimport "./index.css";\nimport App from "./App";\n\ncreateRoot(document.getElementById("root")!).render(<React.StrictMode><App /></React.StrictMode>);`,

  "src/index.css": `@tailwind base;\n@tailwind components;\n@tailwind utilities;\n\n*, *::before, *::after { box-sizing: border-box; }\nhtml, body { margin:0; padding:0; width:100%; height:100%; font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace; font-size:13px; overflow:hidden; background:transparent; color:#f4f4f5; }\n#root { width:100%; height:100%; }\n::-webkit-scrollbar { width:4px; height:4px; }\n::-webkit-scrollbar-track { background:transparent; }\n::-webkit-scrollbar-thumb { background:#525252; border-radius:2px; }\n* { scrollbar-width:thin; scrollbar-color:#525252 transparent; }`,

  "src/lib/utils.ts": `import { clsx, type ClassValue } from "clsx";\nimport { twMerge } from "tailwind-merge";\n\nexport function cn(...inputs: ClassValue[]) {\n  return twMerge(clsx(inputs));\n}`,

  "vite.config.ts": `import { defineConfig } from "vite";\nimport react from "@vitejs/plugin-react";\nimport path from "path";\n\nexport default defineConfig({\n  plugins: [react()],\n  base: "./",\n  resolve: { alias: { "@": path.resolve(__dirname, "./src") } },\n  server: { hmr: false },\n});`,

  "tsconfig.json": JSON.stringify({ compilerOptions: { target: "ES2020", useDefineForClassFields: true, lib: ["ES2020", "DOM", "DOM.Iterable"], module: "ESNext", skipLibCheck: true, moduleResolution: "bundler", allowImportingTsExtensions: true, resolveJsonModule: true, isolatedModules: true, noEmit: true, jsx: "react-jsx", strict: true, noUnusedLocals: false, noUnusedParameters: false, noFallthroughCasesInSwitch: true, paths: { "@/*": ["./src/*"] } }, include: ["src"] }, null, 2),

  "postcss.config.js": `export default { plugins: { tailwindcss: {}, autoprefixer: {} } };`,

  "tailwind.config.ts": `/** @type {import('tailwindcss').Config} */\nexport default { darkMode: "class", content: ["./index.html", "./src/**/*.{ts,tsx}"], theme: { extend: {} }, plugins: [] };`,

  "package.json": JSON.stringify({ name: "widget", private: true, version: "0.0.1", type: "module", scripts: { build: "vite build" }, dependencies: { react: "^18.3.1", "react-dom": "^18.3.1", "class-variance-authority": "^0.7.1", clsx: "^2.1.1", "tailwind-merge": "^2.5.2", "lucide-react": "^0.400.0", recharts: "^2.15.0", "date-fns": "^4.1.0", "maplibre-gl": "^4.7.0", "framer-motion": "^11.0.0", "@tanstack/react-query": "^5.0.0" }, devDependencies: { "@vitejs/plugin-react": "^4.3.1", "@types/react": "^18.3.3", "@types/react-dom": "^18.3.0", tailwindcss: "^3.4.1", autoprefixer: "^10.4.20", postcss: "^8.4.40", typescript: "^5.5.3", vite: "^5.4.1" } }, null, 2),

  "components.json": JSON.stringify({ "$schema": "https://ui.shadcn.com/schema.json", style: "default", rsc: false, tsx: true, tailwind: { config: "tailwind.config.ts", css: "src/index.css", baseColor: "neutral", cssVariables: true }, aliases: { components: "@/components", utils: "@/lib/utils", ui: "@/components/ui", lib: "@/lib", hooks: "@/hooks" } }),
};

const SHADCN_COMPONENTS = "button card badge input table tabs scroll-area skeleton separator progress alert avatar checkbox dialog dropdown-menu label popover radio-group select sheet slider switch textarea toggle tooltip accordion collapsible command context-menu hover-card menubar navigation-menu pagination resizable sonner";

if (existsSync(join(BASE_DIR, "node_modules", ".package-lock.json"))) {
  console.log("[prebuild] Base template already exists, skipping.");
  process.exit(0);
}

console.log("[prebuild] Writing template files to", BASE_DIR);
for (const [filePath, content] of Object.entries(TEMPLATES)) {
  const full = join(BASE_DIR, filePath);
  mkdirSync(dirname(full), { recursive: true });
  writeFileSync(full, content);
}

console.log("[prebuild] Running npm install...");
execSync("npm install --include=dev", {
  cwd: BASE_DIR,
  stdio: "inherit",
  timeout: 120_000,
});

console.log("[prebuild] Installing shadcn components...");
try {
  execSync(`npx shadcn@latest add --yes ${SHADCN_COMPONENTS}`, {
    cwd: BASE_DIR,
    stdio: "inherit",
    timeout: 120_000,
  });
} catch {
  console.warn("[prebuild] Some shadcn components may have failed (non-fatal)");
}

console.log("[prebuild] Base template ready at", BASE_DIR);
