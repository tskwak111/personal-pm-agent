import { readFile, writeFile, mkdir } from "node:fs/promises";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const input = resolve(root, "../../artifacts/openapi.json");
const output = resolve(root, "src/generated/schema.ts");

try {
  const raw = await readFile(input, "utf-8");
  const spec = JSON.parse(raw);
  const paths = Object.keys(spec.paths || {}).join(", ");
  await mkdir(dirname(output), { recursive: true });
  const content = `// Auto-generated from OpenAPI - do not edit
// Paths: ${paths}
export const openApiPaths = ${JSON.stringify(Object.keys(spec.paths || {}), null, 2)} as const;
export type OpenApiSpec = typeof openApiPaths;
`;
  await writeFile(output, content, "utf-8");
  console.log(`generated ${output}`);
} catch (e) {
  console.error(e);
  process.exit(1);
}
