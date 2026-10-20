---
name: opencode-v2-plugins
description: Field-tested notes for building, installing, testing and debugging OpenCode 2 plugins (@opencode/plugin, `export default { id, setup(ctx) }`) and for making their effects show up in OpenChamber. Use this whenever you write or fix an OpenCode v2 plugin, port a v1 plugin (chat.message, experimental.chat.system.transform, tool.execute.*) to v2, hook prompts, skills, tools or sessions, post synthetic messages, or wonder why a plugin's effect isn't visible in OpenChamber. Also covers OpenChamber extensions (@openchamber/sdk) and what they can and can't do.
---

# OpenCode 2 and OpenChamber plugins: field notes

Verified against OpenCode 2.0.32 bundled in OpenChamber 2.4.0 (desktop, Windows), October 2026.
Points marked *(inferred)* were not tested directly. The built-in `opencode` skill covers the official
docs; this skill covers what the docs leave out or what behaved differently than expected.

When something here disagrees with a newer OpenCode version, trust what you observe and update this file.

## 1. v1 → v2: almost everything changed

v1 plugins don't load in v2. The loader fails with "Plugin must export a default definition with an id
and an effect or setup function".

| v1 | v2 |
|---|---|
| `@opencode-ai/plugin`, `async (ctx) => hooks` | `@opencode/plugin`, `export default { id, setup(ctx) }` |
| `chat.message` | `ctx.session.hook("prompt", …)` |
| `experimental.chat.system.transform` | `ctx.session.hook("context", …)` → `event.system` |
| `experimental.chat.messages.transform` | `ctx.session.hook("context", …)` → `event.messages` |
| `tool.execute.before/after` | `ctx.tool.hook("execute.before" / "execute.after", …)` |
| `shell.env` | `ctx.shell.hook("create.before", …)` |
| config key `plugin` | config key `plugins` (plural) |

Other session hooks: `compaction`, `generate`, `title`, `model.request`, `http.request`,
`http.response`, `retry`, `experimental.ws.*`. Each `hook()` returns `{ dispose }`. `setup` may return a
cleanup function. Other `ctx` domains: `skill` (list, transform, reload), `tool` (transform, list),
`storage`, `event.subscribe`, `generate`, `app`, `location`.

**Types without installing anything:** `import type { Plugin } from "@opencode/plugin"` is erased at
runtime, so the package doesn't need to be installed. Use `Plugin.Plugin` / `Plugin.Context`. To read
the real shapes, download the npm tarballs (`@opencode/plugin`, `@opencode/client`, `@opencode/schema`,
`@opencode/ai`). The most complete reference for messages and API inputs is
`@opencode/client/dist/promise/generated/types.d.ts`.

## 2. Minimal plugin and where it loads

```ts
import type { Plugin } from "@opencode/plugin";

const plugin: Plugin.Plugin = {
  id: "my-plugin",
  async setup(ctx) {
    await ctx.session.hook("prompt", async (event) => {
      // event.prompt.text, event.prompt.skills, event.metadata, event.sessionID
    });
  },
};
export default plugin;
```

- **Auto-loaded locations:** `~/.config/opencode/plugins/` (global) and `.opencode/plugins/` (project).
  A folder with a `package.json` whose `main`/`exports` points at `index.ts` works. TypeScript runs as-is
  (OpenCode embeds Bun). Write relative imports with the `.ts` extension (`./core.ts`); that works in
  both Bun and Node's type stripping.
- **Config entries:** since 2026-08, absolute *file* paths in `plugins` are silently dropped (#46551).
  Point at a folder instead.
- **The loader's ID is the full path** (`msg="loading plugin" id="C:\…\plugins\my-plugin"`), not your
  `id`. Disabling with `"plugins": ["-my-plugin"]` or `"-<full path>"` in a project config did not stop a
  global folder plugin from loading. For isolation, use an environment-variable kill switch in your own
  code instead.
- **Hot reload:** the server watches the entry file and its imports, and reloads the plugin when they
  change. OpenChamber picked up a newly copied plugin folder without a restart.
- **`ctx.options` is empty for auto-loaded plugins.** It's only filled by the config object form
  `{ "package": "…", "options": { … } }`. Ship a JSON config next to `index.ts` and find it with
  `dirname(fileURLToPath(import.meta.url))`.
- **`console.*` output goes nowhere useful.** Write your own log file (JSONL works well).
- **`ctx.storage`** holds JSON per plugin, survives restarts, and is shared across server processes.
  It's keyed by plugin `id`: rename the plugin and it starts empty.

## 3. The prompt hook

Event: `{ sessionID, messageID, prompt: { text, files?, agents?, skills? }, metadata?, delivery }`.

- **When it runs:** once per user message, at admission, before attachments and skills are resolved.
  Synthetic, shell and compaction messages skip it. Subagent task briefs are stored as `user` messages,
  so it probably runs for subagents too *(inferred)*.
- **Changes stick:** whatever you set on `event.prompt` and `event.metadata` is stored with the
  message. `metadata` is a good place to record what your plugin did.
- **It blocks the message.** The hook is awaited, so slow work delays the user's message, and **a
  thrown error means the message is not sent**. Put the whole body under one time budget, including
  every `ctx.*` call (a stalled `ctx.session.context()` would otherwise hold the message), and catch
  everything.
- **Attaching a skill:** `event.prompt.skills = [...(event.prompt.skills ?? []), { id }]` makes OpenCode
  load it natively. The result is stored *inside the user message* as `skills[].text`
  (`<skill_content name="…">…`), not as a separate `type: "skill"` message. The model receives it;
  OpenChamber shows nothing.

## 4. The context hook

Runs before *every* model call in the agent loop, including tool continuations. Changes affect only
that outgoing request and are not stored. Editing `event.system` there changes the system prompt each
turn and breaks prompt caching, so put one-time content in the prompt hook instead.

## 5. Skills

- **`ctx.skill.list()`** returns `{ location, data: SkillInfo[] }`. Each item is
  `{ id, name, description?, autoinvoke?, path, content }`.
- **IDs:** `id` is the folder name. The frontmatter `name` is only a display label (a skill with
  `title:` instead of `name:` still works). `content` has the frontmatter already removed.
- **Built-in skills** have virtual paths: `/builtin/opencode.md`, `/builtin/report.md`.
- **Discovery is lazy.** The first `list()` on a freshly started server or location can return `[]`,
  and a moment later returns everything. Never cache an empty result; retry on the next call.
  This also means `opencode api --standalone skill.list` *always* returns `[]`: every standalone call
  starts a fresh server. Ask a server that stays up instead (see section 9).
- **Scanned folders:** `~/.config/opencode/skills`, `~/.claude/skills`, `~/.agents/skills`, plus
  `.opencode/skills`, `.claude/skills` and `.agents/skills` from the project up to its root. The config
  key `skills` adds folders or HTTP catalogs. Flat `.md` files at a source root also count.
- **The model loads skills** with the tool named `skill`, input `{ id }`. Live, you see this through
  `ctx.tool.hook("execute.after")` with `event.tool === "skill"`. In history it's an assistant
  `content[]` part `{ type: "tool", name: "skill", state: { input: { id } } }`.
- **Hiding a skill from the model:** `metadata: { opencode/autoinvoke: false }` or
  `disable-model-invocation: true` in its frontmatter. It can still be loaded explicitly by ID.

## 6. Synthetic messages (`ctx.session.synthetic`)

Input: `{ sessionID, text, description?, metadata?, delivery?: "steer" | "queue", resume? }`.

- **Always pass `resume: false`.** The API "schedules execution unless resume is false", so without it
  a synthetic message starts a model turn of its own.
- **Calling it from inside the prompt hook works:** awaited, it took about 3 ms with no deadlock, and
  it lands immediately *before* the user's message. The model reads it. Wrapping instructions in
  `<system-reminder>…</system-reminder>` worked well.
- **OpenChamber hides synthetic messages,** including the `<system-reminder>` it injects before your
  prompts itself.
- **Use it to make an effect visible.** Since tool calls *are* shown, a synthetic message asking the
  model to "load skill X with the skill tool" produces a visible `skill` call. In testing the model
  loaded the skill as its first action. Only treat it as loaded once the tool call actually happens,
  so a request the model ignores can be repeated.

## 7. Reading session data

- **`ctx.session.context({ sessionID })`** returns the messages currently in context, as an array.
  Message `type` is one of: `user`, `assistant`, `synthetic`, `system`, `skill`, `shell`,
  `compaction`, `idle`, `agent-switched`, `model-switched`, `location-switched`.
- **User message:** `{ text, files?, agents?, skills?: [{ id, name, text }], metadata?, time }`.
- **Assistant message:** `content[]` holds `text`, `reasoning` and `tool` parts. Tool parts have
  `name` and `state.input`.

## 8. OpenChamber specifics

- **Its own OpenCode.** OpenChamber bundles its own CLI
  (`%LOCALAPPDATA%\Programs\@openchamberelectron\resources\opencode-cli\opencode.exe` on Windows) and
  runs `opencode serve --hostname 127.0.0.1 --port <random>`. Its log is
  `%APPDATA%\OpenChamber\logs\main.log`. Closing the app stops that server.
- **Plugins list:** Settings → Plugins lists OpenCode plugins with a "Loaded" badge.
- **What the chat shows:** tool calls, including `skill` loads. It does **not** show skills attached
  through `prompt.skills`, synthetic or system messages, or message `metadata`.
- **OpenChamber extensions are a different thing from OpenCode plugins.** `@openchamber/sdk` "guests"
  are sandboxed iframes, installed under Settings → Extensions, with prebuilt IIFE JavaScript. They
  can add panels, full pages, Work Status sections, popovers, toasts, slash commands, file editors and
  styling rules for tool calls (`contributes.tools`). They read files only through declared globs.
  They **cannot** add chat messages or reveal hidden ones.

## 9. Testing and debugging

- **Unit-test the real plugin in Node 22.6+** (it runs `.ts` directly): import `index.ts`, call
  `setup()` with a fake `ctx` that records hook callbacks, then call them yourself.

  ```ts
  const hooks: Record<string, (e: any) => unknown> = {};
  const reg = async (n: string, cb: any) => ((hooks[n] = cb), { dispose: async () => {} });
  const ctx: any = {
    options: {}, storage: { get: async () => undefined, set: async () => {}, remove: async () => {} },
    skill: { list: async () => ({ data: [] }) },
    session: { context: async () => [], synthetic: async () => {}, hook: (n: string, cb: any) => reg(`session.${n}`, cb) },
    tool: { hook: (n: string, cb: any) => reg(`tool.${n}`, cb) },
  };
  await plugin.setup(ctx);
  await hooks["session.prompt"]({ sessionID: "s", messageID: "m", prompt: { text: "hi" }, delivery: "steer" });
  ```

- **End-to-end:** `opencode run --standalone --format json "message"` prints `step_start`,
  `tool_use` and `text` events. It uses the real model and adds a session to your history.
- **API from the CLI:** `opencode api --standalone <operationId> --param key=value`. Useful IDs:
  `skill.list`, `session.list`, `session.context`, `session.message.list` (not `message.list`). For
  message lists, `limit` is at most 200 and `cursor` can't be combined with `order`.
- **Without `--standalone`,** `opencode api`, `plugin list` and `debug config` start a background
  service (`serve --service`) that keeps running. Stop it with `opencode service stop`.
- **Logs:** add `--print-logs --log-level debug` to `--standalone` commands to see server logs. The
  shared log is `~/.local/share/opencode/log/opencode.log`. Paths: `opencode debug paths`.
  The `plugin.list` API returned an empty list even while a folder plugin was loaded; check the
  `loading plugin` log line instead.
- **A server you control:** `opencode serve --port N` prints a one-time password in its log. Use HTTP
  Basic auth `opencode:<password>`. Routes look like `/api/skill`, `/api/session` and
  `/api/session/:id/message`. This is the reliable way to list skills: call `/api/skill` twice.
- **Testing a copy next to the installed plugin:** give the copy a different `id` and switch the
  installed one off with an environment variable your code checks.
- **Known flake:** the first-ever run of a brand-new plugin `id` hung twice, with no output from the
  plugin, then worked every time after. If a first run hangs, retry before debugging.
- **v1 config files still load,** but you'll see "configuration normalization diagnostic" warnings,
  and v1-only model keys are dropped.
