var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// src/main.ts
var main_exports = {};
__export(main_exports, {
  default: () => ObsidianLinkerPlugin
});
module.exports = __toCommonJS(main_exports);
var import_obsidian = require("obsidian");

// src/linker.ts
var CODE_BLOCK = /```[\s\S]*?```/g;
var INLINE_CODE = /`[^`]*`/g;
var EMBED = /!\[\[(?:[^\]|]+\|)?[^\]]+\]\]/g;
var MD_LINK = /\[[^\]]+\]\([^)]+\)/g;
var WIKILINK = /(?<!!)\[\[(?:[^\]|]+\|)?[^\]]+\]\]/g;
var WIKILINK_CAPTURE = /(?<!!)\[\[([^\]]+)\]\]/g;
var METADATA = /---\s*\n([\s\S]*?)\n\s*---/;
var HEADING_LINE = /^(\s{0,3}#{1,6}\s.+)$/gm;
var FIRST_H1 = /^#\s+(.+?)\s*$/m;
function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
function formatWikilink(canonical, matched) {
  if (matched.toLocaleLowerCase() === canonical.toLocaleLowerCase()) {
    return `[[${matched}]]`;
  }
  return `[[${canonical}|${matched}]]`;
}
function stripYamlScalar(value) {
  const trimmed = value.trim();
  if (trimmed.length >= 2 && (trimmed.startsWith('"') && trimmed.endsWith('"') || trimmed.startsWith("'") && trimmed.endsWith("'"))) {
    return trimmed.slice(1, -1);
  }
  return trimmed;
}
function parseAliases(metadata) {
  if (!metadata)
    return [];
  let inner = metadata.trim();
  if (inner.startsWith("---"))
    inner = inner.slice(3);
  if (inner.endsWith("---"))
    inner = inner.slice(0, -3);
  const aliases = [];
  const lines = inner.split("\n");
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const aliasMatch = line.match(/^alias:\s*(.+)$/);
    if (aliasMatch) {
      aliases.push(stripYamlScalar(aliasMatch[1]));
      continue;
    }
    const inlineMatch = line.match(/^aliases:\s*\[(.*)\]\s*$/);
    if (inlineMatch) {
      for (const part of inlineMatch[1].split(",")) {
        if (part.trim())
          aliases.push(stripYamlScalar(part));
      }
      continue;
    }
    if (/^aliases:\s*$/.test(line)) {
      i += 1;
      while (i < lines.length && /^\s+-\s+/.test(lines[i])) {
        aliases.push(stripYamlScalar(lines[i].replace(/^\s+-\s+/, "")));
        i += 1;
      }
    }
  }
  return aliases;
}
function parseFirstH1(body) {
  const match = body.match(FIRST_H1);
  return match ? match[1].trim() : null;
}
function phraseIgnored(phrase, options) {
  const trimmed = phrase.trim();
  if (!trimmed || trimmed.length < options.minTitleLength)
    return true;
  return options.ignorePhrases.has(trimmed.toLocaleLowerCase());
}
function parseWikilinkInner(inner) {
  if (inner.includes("|")) {
    const [left, display] = inner.split("|", 2);
    const target2 = left.split("#", 1)[0].trim();
    return [target2, display.trim()];
  }
  const target = inner.split("#", 1)[0].trim();
  return [target, target];
}
function buildManagedLinkKeys(phrases) {
  const keys = /* @__PURE__ */ new Map();
  for (const entry of phrases) {
    keys.set(
      `${entry.canonical.toLocaleLowerCase()}\0${entry.phrase.toLocaleLowerCase()}`,
      entry
    );
  }
  return keys;
}
function buildPhrases(files, options) {
  var _a, _b, _c, _d, _e, _f;
  const byTitle = /* @__PURE__ */ new Map();
  for (const file of files) {
    const title = (_b = (_a = file.path.split("/").pop()) == null ? void 0 : _a.replace(/\.md$/i, "")) != null ? _b : "";
    const key = title.toLocaleLowerCase();
    const paths = (_c = byTitle.get(key)) != null ? _c : [];
    paths.push(file.path);
    byTitle.set(key, paths);
  }
  const winners = /* @__PURE__ */ new Map();
  for (const [titleLower, paths] of byTitle.entries()) {
    winners.set(titleLower, paths.sort((a, b) => b.length - a.length)[0]);
  }
  const phraseMap = /* @__PURE__ */ new Map();
  const register = (phrase, canonical, sourcePath) => {
    if (phraseIgnored(phrase, options))
      return;
    const key = phrase.toLocaleLowerCase();
    phraseMap.set(key, { phrase, canonical, sourcePath });
  };
  for (const file of files) {
    const canonical = (_e = (_d = file.path.split("/").pop()) == null ? void 0 : _d.replace(/\.md$/i, "")) != null ? _e : "";
    const titleLower = canonical.toLocaleLowerCase();
    if (winners.get(titleLower) === file.path) {
      register(canonical, canonical, file.path);
    }
    const metadataMatch = METADATA.exec(file.content);
    const metadata = (_f = metadataMatch == null ? void 0 : metadataMatch[0]) != null ? _f : "";
    let body = file.content;
    if (metadata)
      body = body.replace(metadata, "");
    if (options.useAliases) {
      for (const alias of parseAliases(metadata)) {
        register(alias, canonical, file.path);
      }
    }
    if (options.useHeadings) {
      const heading = parseFirstH1(body);
      if (heading)
        register(heading, canonical, file.path);
    }
  }
  return Array.from(phraseMap.values()).sort(
    (a, b) => b.phrase.length - a.phrase.length
  );
}
function lineNumberAt(content, index) {
  return content.slice(0, index).split("\n").length;
}
function protect(content, skipHeadings) {
  const parts = [];
  let index = 0;
  const stash = (pattern) => {
    content = content.replace(pattern, (match) => {
      const token = `<PH_${index++}>`;
      parts.push(match);
      return token;
    });
  };
  stash(CODE_BLOCK);
  stash(INLINE_CODE);
  stash(EMBED);
  stash(MD_LINK);
  if (skipHeadings)
    stash(HEADING_LINE);
  return [content, parts];
}
function unprotect(content, parts) {
  return content.replace(/<PH_(\d+)>/g, (_, index) => {
    var _a;
    return (_a = parts[Number(index)]) != null ? _a : "";
  });
}
function prepareForLinking(content, skipHeadings) {
  var _a;
  let working = content;
  const metadataMatch = METADATA.exec(working);
  const metadata = (_a = metadataMatch == null ? void 0 : metadataMatch[0]) != null ? _a : "";
  if (metadata)
    working = working.replace(metadata, "<METADATA_SECTION>");
  const [protectedContent, stashed] = protect(working, skipHeadings);
  return [protectedContent, metadata, stashed];
}
function finalizeContent(protectedContent, metadata, stashed) {
  let restored = unprotect(protectedContent, stashed);
  if (metadata)
    restored = restored.replace("<METADATA_SECTION>", metadata);
  return restored;
}
function linkContent(content, phrases, sourcePath, options) {
  let linksAdded = 0;
  const [protectedContent, metadata, stashed] = prepareForLinking(
    content,
    options.skipHeadings
  );
  const withoutLinks = protectedContent.replace(WIKILINK, "");
  let working = protectedContent;
  for (const entry of phrases) {
    if (options.noSelfLinks && entry.sourcePath === sourcePath)
      continue;
    if (!withoutLinks.toLocaleLowerCase().includes(entry.phrase.toLocaleLowerCase())) {
      continue;
    }
    const pattern = new RegExp(
      `(?<!\\[\\[)\\b${escapeRegExp(entry.phrase)}\\b(?!\\]\\])`,
      "gi"
    );
    working = working.replace(pattern, (matched) => {
      linksAdded += 1;
      return formatWikilink(entry.canonical, matched);
    });
  }
  return {
    content: finalizeContent(working, metadata, stashed),
    linksAdded
  };
}
function unlinkContent(content, managedKeys, sourcePath, options) {
  const changes = [];
  let removed = 0;
  const [protectedContent, metadata, stashed] = prepareForLinking(
    content,
    options.skipHeadings
  );
  let working = protectedContent;
  working = working.replace(
    WIKILINK_CAPTURE,
    (full, inner, offset) => {
      const [target, display] = parseWikilinkInner(inner);
      const key = `${target.toLocaleLowerCase()}\0${display.toLocaleLowerCase()}`;
      const entry = managedKeys.get(key);
      if (!entry)
        return full;
      if (options.noSelfLinks && entry.sourcePath === sourcePath)
        return full;
      removed += 1;
      changes.push({
        line: lineNumberAt(working, offset),
        wikilink: full,
        restoredText: display
      });
      return display;
    }
  );
  return {
    content: finalizeContent(working, metadata, stashed),
    linksRemoved: removed,
    changes
  };
}
function scanWikilinks(content, skipHeadings) {
  var _a;
  const [protectedContent, metadata, _stashed] = prepareForLinking(content, skipHeadings);
  let working = protectedContent;
  if (metadata)
    working = working.replace("<METADATA_SECTION>", "");
  const found = [];
  for (const match of working.matchAll(WIKILINK_CAPTURE)) {
    const inner = match[1];
    const [target] = parseWikilinkInner(inner);
    found.push({
      line: lineNumberAt(working, (_a = match.index) != null ? _a : 0),
      wikilink: match[0],
      target
    });
  }
  return found;
}
function auditVault(files, options) {
  var _a, _b, _c;
  const phrases = buildPhrases(files, options);
  const knownTitles = new Set(
    files.map((file) => {
      var _a2, _b2;
      return (_b2 = (_a2 = file.path.split("/").pop()) == null ? void 0 : _a2.replace(/\.md$/i, "")) != null ? _b2 : "";
    }).map(
      (t) => t.toLocaleLowerCase()
    )
  );
  let pendingLinks = 0;
  let pendingFiles = 0;
  const backlinkCounts = /* @__PURE__ */ new Map();
  for (const file of files) {
    const { linksAdded } = linkContent(file.content, phrases, file.path, options);
    if (linksAdded > 0) {
      pendingLinks += linksAdded;
      pendingFiles += 1;
    }
    for (const link of scanWikilinks(file.content, options.skipHeadings)) {
      const key = link.target.toLocaleLowerCase();
      backlinkCounts.set(key, ((_a = backlinkCounts.get(key)) != null ? _a : 0) + 1);
    }
  }
  const brokenLinks = [];
  for (const file of files) {
    for (const link of scanWikilinks(file.content, options.skipHeadings)) {
      if (!knownTitles.has(link.target.toLocaleLowerCase())) {
        brokenLinks.push({
          filePath: file.path,
          line: link.line,
          target: link.target,
          wikilink: link.wikilink
        });
      }
    }
  }
  const titleByLower = /* @__PURE__ */ new Map();
  for (const file of files) {
    const title = (_c = (_b = file.path.split("/").pop()) == null ? void 0 : _b.replace(/\.md$/i, "")) != null ? _c : "";
    titleByLower.set(title.toLocaleLowerCase(), title);
  }
  const zeroBacklinkNotes = Array.from(titleByLower.values()).filter((title) => {
    var _a2;
    return ((_a2 = backlinkCounts.get(title.toLocaleLowerCase())) != null ? _a2 : 0) === 0;
  }).sort();
  const topLinkedTitles = Array.from(backlinkCounts.entries()).sort((a, b) => b[1] - a[1]).slice(0, 10).map(([key, count]) => {
    var _a2;
    return {
      title: (_a2 = titleByLower.get(key)) != null ? _a2 : key,
      count
    };
  });
  return {
    pendingLinks,
    pendingFiles,
    brokenLinks,
    zeroBacklinkNotes,
    topLinkedTitles
  };
}

// src/main.ts
var DEFAULT_SETTINGS = {
  noSelfLinks: true,
  useAliases: true,
  useHeadings: false,
  skipHeadings: true,
  minTitleLength: 1,
  ignorePhrases: "README"
};
var ObsidianLinkerPlugin = class extends import_obsidian.Plugin {
  constructor() {
    super(...arguments);
    this.settings = DEFAULT_SETTINGS;
  }
  async onload() {
    await this.loadSettings();
    this.addCommand({
      id: "link-vault-titles",
      name: "Link note titles in vault",
      callback: () => this.promptAndRun("link", false)
    });
    this.addCommand({
      id: "link-vault-titles-dry-run",
      name: "Preview title links (dry run)",
      callback: () => this.promptAndRun("link", true)
    });
    this.addCommand({
      id: "audit-vault-links",
      name: "Audit vault links",
      callback: () => this.runAudit()
    });
    this.addCommand({
      id: "unlink-vault-titles",
      name: "Remove managed title links",
      callback: () => this.promptAndRun("unlink", false)
    });
    this.addCommand({
      id: "unlink-vault-titles-dry-run",
      name: "Preview removing managed links",
      callback: () => this.promptAndRun("unlink", true)
    });
    this.addSettingTab(new LinkerSettingTab(this.app, this));
  }
  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }
  async saveSettings() {
    await this.saveData(this.settings);
  }
  linkerOptions() {
    return {
      noSelfLinks: this.settings.noSelfLinks,
      useAliases: this.settings.useAliases,
      useHeadings: this.settings.useHeadings,
      skipHeadings: this.settings.skipHeadings,
      minTitleLength: this.settings.minTitleLength,
      ignorePhrases: new Set(
        this.settings.ignorePhrases.split("\n").map((line) => line.trim().toLocaleLowerCase()).filter(Boolean)
      )
    };
  }
  async loadFilePayload() {
    const files = this.app.vault.getMarkdownFiles();
    const filePayload = [];
    for (const file of files) {
      filePayload.push({
        path: file.path,
        content: await this.app.vault.read(file)
      });
    }
    return { files, filePayload };
  }
  promptAndRun(mode, dryRun) {
    const modal = new ConfirmLinkerModal(this.app, mode, dryRun, () => {
      if (mode === "link")
        this.runLinker(dryRun);
      else
        this.runUnlink(dryRun);
    });
    modal.open();
  }
  async runLinker(dryRun) {
    var _a, _b;
    const { files, filePayload } = await this.loadFilePayload();
    const options = this.linkerOptions();
    const phrases = buildPhrases(filePayload, options);
    let totalLinks = 0;
    let editedFiles = 0;
    for (const file of files) {
      const original = (_b = (_a = filePayload.find((entry) => entry.path === file.path)) == null ? void 0 : _a.content) != null ? _b : "";
      const { content, linksAdded } = linkContent(
        original,
        phrases,
        file.path,
        options
      );
      if (linksAdded === 0)
        continue;
      totalLinks += linksAdded;
      editedFiles += 1;
      if (!dryRun)
        await this.app.vault.modify(file, content);
    }
    const summary = dryRun ? `Would add ${totalLinks} links in ${editedFiles} notes.` : `Added ${totalLinks} links in ${editedFiles} notes.`;
    new import_obsidian.Notice(summary);
  }
  async runUnlink(dryRun) {
    var _a, _b;
    const { files, filePayload } = await this.loadFilePayload();
    const options = this.linkerOptions();
    const phrases = buildPhrases(filePayload, options);
    const managedKeys = buildManagedLinkKeys(phrases);
    let totalRemoved = 0;
    let editedFiles = 0;
    for (const file of files) {
      const original = (_b = (_a = filePayload.find((entry) => entry.path === file.path)) == null ? void 0 : _a.content) != null ? _b : "";
      const { content, linksRemoved } = unlinkContent(
        original,
        managedKeys,
        file.path,
        options
      );
      if (linksRemoved === 0)
        continue;
      totalRemoved += linksRemoved;
      editedFiles += 1;
      if (!dryRun)
        await this.app.vault.modify(file, content);
    }
    const summary = dryRun ? `Would remove ${totalRemoved} links in ${editedFiles} notes.` : `Removed ${totalRemoved} links in ${editedFiles} notes.`;
    new import_obsidian.Notice(summary);
  }
  async runAudit() {
    const { filePayload } = await this.loadFilePayload();
    const report = auditVault(filePayload, this.linkerOptions());
    const modal = new AuditReportModal(this.app, report);
    modal.open();
  }
};
var ConfirmLinkerModal = class extends import_obsidian.Modal {
  constructor(app, mode, dryRun, onConfirm) {
    super(app);
    this.mode = mode;
    this.dryRun = dryRun;
    this.onConfirm = onConfirm;
  }
  onOpen() {
    const { contentEl } = this;
    const titles = {
      link: this.dryRun ? "Preview title links?" : "Link note titles?",
      unlink: this.dryRun ? "Preview removing links?" : "Remove managed links?"
    };
    const bodies = {
      link: this.dryRun ? "This will scan your vault and report how many links would be added." : "This will modify notes in your vault. Consider a backup or sync commit first.",
      unlink: this.dryRun ? "This will report how many managed title/alias links would be removed." : "This removes wikilinks created by the same rules as Link note titles. Other links are kept."
    };
    contentEl.createEl("h2", { text: titles[this.mode] });
    contentEl.createEl("p", { text: bodies[this.mode] });
    contentEl.createEl("button", { text: "Continue", type: "button" }).onclick = () => {
      this.close();
      this.onConfirm();
    };
    contentEl.createEl("button", { text: "Cancel", type: "button" }).onclick = () => this.close();
  }
  onClose() {
    this.contentEl.empty();
  }
};
var AuditReportModal = class extends import_obsidian.Modal {
  constructor(app, report) {
    super(app);
    this.report = report;
  }
  onOpen() {
    const { contentEl } = this;
    contentEl.createEl("h2", { text: "Vault link audit" });
    contentEl.createEl("p", {
      text: `Pending links: ${this.report.pendingLinks} in ${this.report.pendingFiles} notes`
    });
    contentEl.createEl("p", {
      text: `Broken wikilinks: ${this.report.brokenLinks.length}`
    });
    if (this.report.brokenLinks.length > 0) {
      const list = contentEl.createEl("ul");
      for (const broken of this.report.brokenLinks.slice(0, 20)) {
        list.createEl("li", {
          text: `${broken.filePath}:${broken.line}: ${broken.wikilink} \u2192 missing '${broken.target}'`
        });
      }
      if (this.report.brokenLinks.length > 20) {
        list.createEl("li", {
          text: `\u2026 and ${this.report.brokenLinks.length - 20} more`
        });
      }
    }
    contentEl.createEl("p", {
      text: `Notes with zero incoming links: ${this.report.zeroBacklinkNotes.length}`
    });
    if (this.report.topLinkedTitles.length > 0) {
      contentEl.createEl("h3", { text: "Most linked titles" });
      const top = contentEl.createEl("ul");
      for (const entry of this.report.topLinkedTitles) {
        top.createEl("li", { text: `${entry.title} (${entry.count})` });
      }
    }
  }
  onClose() {
    this.contentEl.empty();
  }
};
var LinkerSettingTab = class extends import_obsidian.PluginSettingTab {
  constructor(app, plugin) {
    super(app, plugin);
    this.plugin = plugin;
  }
  display() {
    const { containerEl } = this;
    containerEl.empty();
    containerEl.createEl("h2", { text: "Obsidian Linker" });
    new import_obsidian.Setting(containerEl).setName("No self links").setDesc("Do not link a note title inside its own file.").addToggle(
      (toggle) => toggle.setValue(this.plugin.settings.noSelfLinks).onChange(async (value) => {
        this.plugin.settings.noSelfLinks = value;
        await this.plugin.saveSettings();
      })
    );
    new import_obsidian.Setting(containerEl).setName("Use aliases").setDesc("Use YAML alias / aliases fields from front matter.").addToggle(
      (toggle) => toggle.setValue(this.plugin.settings.useAliases).onChange(async (value) => {
        this.plugin.settings.useAliases = value;
        await this.plugin.saveSettings();
      })
    );
    new import_obsidian.Setting(containerEl).setName("Use H1 headings").setDesc("Also treat each note's first # heading as a link phrase.").addToggle(
      (toggle) => toggle.setValue(this.plugin.settings.useHeadings).onChange(async (value) => {
        this.plugin.settings.useHeadings = value;
        await this.plugin.saveSettings();
      })
    );
    new import_obsidian.Setting(containerEl).setName("Skip headings").setDesc("Do not add links on markdown heading lines.").addToggle(
      (toggle) => toggle.setValue(this.plugin.settings.skipHeadings).onChange(async (value) => {
        this.plugin.settings.skipHeadings = value;
        await this.plugin.saveSettings();
      })
    );
    new import_obsidian.Setting(containerEl).setName("Minimum title length").setDesc("Ignore link phrases shorter than this length.").addText(
      (text) => text.setPlaceholder("1").setValue(String(this.plugin.settings.minTitleLength)).onChange(async (value) => {
        const parsed = Number.parseInt(value, 10);
        this.plugin.settings.minTitleLength = Number.isFinite(parsed) ? parsed : 1;
        await this.plugin.saveSettings();
      })
    );
    new import_obsidian.Setting(containerEl).setName("Ignored phrases").setDesc("One phrase per line (case-insensitive).").addTextArea(
      (text) => text.setValue(this.plugin.settings.ignorePhrases).onChange(async (value) => {
        this.plugin.settings.ignorePhrases = value;
        await this.plugin.saveSettings();
      })
    );
  }
};
