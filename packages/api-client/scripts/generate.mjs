import { execFileSync } from "node:child_process";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const input = resolve(root, "../../artifacts/openapi.json");
const output = resolve(root, "src/generated/schema.ts");

const executable = resolve(
  root,
  `node_modules/.bin/openapi-typescript${process.platform === "win32" ? ".cmd" : ""}`,
);

execFileSync(executable, [input, "--output", output], { stdio: "inherit" });
