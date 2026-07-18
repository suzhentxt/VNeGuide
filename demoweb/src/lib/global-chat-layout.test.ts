import assert from "node:assert/strict";
import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const appDirectory = fileURLToPath(new URL("../app", import.meta.url));
const rootLayoutPath = path.join(appDirectory, "layout.tsx");
const chatWidgetPath = fileURLToPath(
  new URL("../components/chat/ChatWidget.tsx", import.meta.url),
);
const workspaceProviderPath = fileURLToPath(
  new URL(
    "../components/workspace/ProcedureWorkspaceProvider.tsx",
    import.meta.url,
  ),
);
const chatWidgetElement = /<ChatWidget(?:\s[^>]*)?\s*\/>/g;
const providerOpenElement = /<ProcedureWorkspaceProvider(?:\s[^>]*)?>/g;
const providerCloseElement = /<\/ProcedureWorkspaceProvider\s*>/g;

function countMatches(source: string, pattern: RegExp): number {
  return [...source.matchAll(pattern)].length;
}

async function findLayoutFiles(directory: string): Promise<string[]> {
  const entries = await readdir(directory, { withFileTypes: true });
  const files: string[] = [];

  for (const entry of entries) {
    const entryPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await findLayoutFiles(entryPath)));
    } else if (entry.isFile() && entry.name === "layout.tsx") {
      files.push(entryPath);
    }
  }

  return files;
}

test("root layout mounts one global chat inside one workspace provider", async () => {
  const source = await readFile(rootLayoutPath, "utf8");

  assert.equal(countMatches(source, providerOpenElement), 1);
  assert.equal(countMatches(source, providerCloseElement), 1);
  assert.equal(countMatches(source, chatWidgetElement), 1);

  const providerStart = source.search(/<ProcedureWorkspaceProvider(?:\s[^>]*)?>/);
  const children = source.indexOf("{children}", providerStart);
  const chat = source.search(/<ChatWidget(?:\s[^>]*)?\s*\/>/);
  const providerEnd = source.search(/<\/ProcedureWorkspaceProvider\s*>/);

  assert.ok(providerStart < children, "the provider must wrap the routed page");
  assert.ok(children < chat, "the global chat must render after the routed page");
  assert.ok(chat < providerEnd, "the global chat must stay inside the provider");
});

test("no nested app layout mounts another chat or workspace provider", async () => {
  const layoutFiles = await findLayoutFiles(appDirectory);
  const nestedLayouts = layoutFiles.filter(
    (layoutPath) => path.resolve(layoutPath) !== path.resolve(rootLayoutPath),
  );

  for (const layoutPath of nestedLayouts) {
    const source = await readFile(layoutPath, "utf8");
    const relativePath = path.relative(appDirectory, layoutPath);

    assert.equal(
      countMatches(source, chatWidgetElement),
      0,
      `${relativePath} must not mount ChatWidget`,
    );
    assert.equal(
      countMatches(source, providerOpenElement),
      0,
      `${relativePath} must not mount ProcedureWorkspaceProvider`,
    );
  }
});

test("rebind waits for active form synchronization", async () => {
  const source = await readFile(chatWidgetPath, "utf8");

  assert.match(source, /disabled=\{busy \|\| formSyncing\}/);
  assert.match(source, /formSyncing\s*\?\s*"Đang đồng bộ biểu mẫu…"/);
});

test("queued field commits read the latest workspace value when they execute", async () => {
  const source = await readFile(workspaceProviderPath, "utf8");

  assert.match(source, /const field = snapshot\.fields\[fieldId\]/);
  assert.match(source, /value: field\.value/);
  assert.doesNotMatch(source, /performFieldCommit\(fieldId,\s*value\)/);
});

test("workspace keeps an in-memory fallback when session storage is unavailable", async () => {
  const source = await readFile(workspaceProviderPath, "utf8");

  assert.match(source, /const inMemoryWorkspaces = useRef/);
  assert.match(source, /inMemoryWorkspaces\.current\.set\(/);
  assert.match(
    source,
    /inMemoryWorkspaces\.current\.get\(procedureCode\) \?\? readPersisted\(procedureCode\)/,
  );
});
