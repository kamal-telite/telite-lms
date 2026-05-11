import { webcrypto } from "node:crypto";

if (!globalThis.crypto?.getRandomValues) {
  Object.defineProperty(globalThis, "crypto", {
    value: webcrypto,
    configurable: true,
  });
}

await import(new URL("../node_modules/vite/bin/vite.js", import.meta.url));
