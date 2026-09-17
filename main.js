"use strict";
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
  default: () => VaultLinkerPlugin
});
module.exports = __toCommonJS(main_exports);
var import_obsidian3 = require("obsidian");

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
function formatWikilink(canonical, matched, caseSensitive) {
  const same = caseSensitive ? matched === canonical : matched.toLocaleLowerCase() === canonical.toLocaleLowerCase();
  if (same) {
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
    const key = options.caseSensitive ? phrase : phrase.toLocaleLowerCase();
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
  const linkedPhraseKeys = /* @__PURE__ */ new Set();
  for (const entry of phrases) {
    if (options.noSelfLinks && entry.sourcePath === sourcePath)
      continue;
    const phraseKey = options.caseSensitive ? entry.phrase : entry.phrase.toLocaleLowerCase();
    const haystack = options.caseSensitive ? withoutLinks : withoutLinks.toLocaleLowerCase();
    const needle = options.caseSensitive ? entry.phrase : entry.phrase.toLocaleLowerCase();
    if (!haystack.includes(needle)) {
      continue;
    }
    const pattern = new RegExp(
      `(?<!\\[\\[)\\b${escapeRegExp(entry.phrase)}\\b(?!\\]\\])`,
      options.caseSensitive ? "g" : "gi"
    );
    working = working.replace(pattern, (matched) => {
      if (options.firstLinkPerPhrase && linkedPhraseKeys.has(phraseKey)) {
        return matched;
      }
      if (options.firstLinkPerPhrase) {
        linkedPhraseKeys.add(phraseKey);
      }
      linksAdded += 1;
      return formatWikilink(entry.canonical, matched, options.caseSensitive);
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
  const [protectedContent, metadata] = prepareForLinking(content, skipHeadings);
  let working = protectedContent;
  if (metadata)
    working = working.replace("<METADATA_SECTION>", "");
  const found = [];
  const wikilinkRe = new RegExp(WIKILINK_CAPTURE.source, WIKILINK_CAPTURE.flags);
  let match;
  while ((match = wikilinkRe.exec(working)) !== null) {
    const inner = match[1];
    if (inner === void 0)
      continue;
    const [target] = parseWikilinkInner(inner);
    found.push({
      line: lineNumberAt(working, match.index),
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

// src/modals.ts
var import_obsidian = require("obsidian");

// src/audit-report.ts
function formatAuditReportMarkdown(report) {
  const lines = [
    "# Vault Linker audit",
    "",
    `- Pending links (would add): **${String(report.pendingLinks)}** in **${String(report.pendingFiles)}** notes`,
    `- Broken wikilinks: **${String(report.brokenLinks.length)}**`,
    `- Notes with zero incoming links: **${String(report.zeroBacklinkNotes.length)}**`,
    ""
  ];
  if (report.brokenLinks.length > 0) {
    lines.push("## Broken wikilinks", "");
    for (const broken of report.brokenLinks) {
      lines.push(
        `- \`${broken.filePath}:${String(broken.line)}\` ${broken.wikilink} \u2192 missing \`${broken.target}\``
      );
    }
    lines.push("");
  }
  if (report.zeroBacklinkNotes.length > 0) {
    lines.push("## Zero incoming links", "");
    for (const title of report.zeroBacklinkNotes.slice(0, 100)) {
      lines.push(`- ${title}`);
    }
    if (report.zeroBacklinkNotes.length > 100) {
      lines.push(`- \u2026 and ${String(report.zeroBacklinkNotes.length - 100)} more`);
    }
    lines.push("");
  }
  if (report.topLinkedTitles.length > 0) {
    lines.push("## Most linked titles", "");
    for (const entry of report.topLinkedTitles) {
      lines.push(`- ${entry.title} (${String(entry.count)})`);
    }
    lines.push("");
  }
  lines.push("_Generated by Vault Linker_");
  return lines.join("\n");
}

// src/modals.ts
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
    new import_obsidian.Setting(contentEl).setName(titles[this.mode]).setHeading();
    contentEl.createEl("p", { text: bodies[this.mode] });
    const continueButton = contentEl.createEl("button", {
      text: "Continue",
      type: "button"
    });
    continueButton.onclick = () => {
      this.close();
      this.onConfirm();
    };
    const cancelButton = contentEl.createEl("button", {
      text: "Cancel",
      type: "button"
    });
    cancelButton.onclick = () => {
      this.close();
    };
  }
  onClose() {
    this.contentEl.empty();
  }
};
var AuditReportModal = class extends import_obsidian.Modal {
  constructor(app, report) {
    super(app);
    this.report = report;
    this.markdown = formatAuditReportMarkdown(report);
  }
  onOpen() {
    const { contentEl } = this;
    new import_obsidian.Setting(contentEl).setName("Vault link audit").setHeading();
    contentEl.createEl("p", {
      text: `Pending links: ${String(this.report.pendingLinks)} in ${String(this.report.pendingFiles)} notes`
    });
    contentEl.createEl("p", {
      text: `Broken wikilinks: ${String(this.report.brokenLinks.length)}`
    });
    if (this.report.brokenLinks.length > 0) {
      const list = contentEl.createEl("ul");
      for (const broken of this.report.brokenLinks.slice(0, 20)) {
        list.createEl("li", {
          text: `${broken.filePath}:${String(broken.line)}: ${broken.wikilink} \u2192 missing '${broken.target}'`
        });
      }
      if (this.report.brokenLinks.length > 20) {
        list.createEl("li", {
          text: `\u2026 and ${String(this.report.brokenLinks.length - 20)} more`
        });
      }
    }
    contentEl.createEl("p", {
      text: `Notes with zero incoming links: ${String(this.report.zeroBacklinkNotes.length)}`
    });
    if (this.report.topLinkedTitles.length > 0) {
      new import_obsidian.Setting(contentEl).setName("Most linked titles").setHeading();
      const top = contentEl.createEl("ul");
      for (const entry of this.report.topLinkedTitles) {
        top.createEl("li", { text: `${entry.title} (${String(entry.count)})` });
      }
    }
    const actions = contentEl.createDiv({ cls: "vault-linker-audit-actions" });
    const copyButton = actions.createEl("button", { text: "Copy Markdown report", type: "button" });
    copyButton.onclick = () => {
      void navigator.clipboard.writeText(this.markdown).then(() => {
        new import_obsidian.Notice("Audit report copied to clipboard");
      });
    };
    const saveButton = actions.createEl("button", { text: "Save report in vault", type: "button" });
    saveButton.onclick = () => {
      void this.saveReportInVault();
    };
  }
  async saveReportInVault() {
    const stamp = (/* @__PURE__ */ new Date()).toISOString().replace(/[:.]/g, "-").slice(0, 19);
    const path = `.obsidian/vault-linker-audit-${stamp}.md`;
    const existing = this.app.vault.getAbstractFileByPath(path);
    if (existing instanceof import_obsidian.TFile) {
      await this.app.vault.modify(existing, this.markdown);
    } else {
      await this.app.vault.create(path, this.markdown);
    }
    new import_obsidian.Notice(`Saved audit to ${path}`);
  }
  onClose() {
    this.contentEl.empty();
  }
};

// src/settings-storage.ts
var DEFAULT_SETTINGS = {
  noSelfLinks: true,
  useAliases: true,
  useHeadings: false,
  skipHeadings: true,
  minTitleLength: 1,
  ignorePhrases: "README",
  caseSensitive: false,
  firstLinkPerPhrase: false,
  includeGlobs: "",
  excludeGlobs: ""
};
var SETTING_COPY = {
  noSelfLinks: {
    name: "No self links",
    desc: "Do not link a note title inside its own file."
  },
  useAliases: {
    name: "Use aliases",
    desc: "Use YAML alias / aliases fields from front matter."
  },
  useHeadings: {
    name: "Use h1 headings",
    desc: "Also treat each note's first # heading as a link phrase."
  },
  skipHeadings: {
    name: "Skip headings",
    desc: "Do not add links on Markdown heading lines."
  },
  minTitleLength: {
    name: "Minimum title length",
    desc: "Ignore link phrases shorter than this length."
  },
  ignorePhrases: {
    name: "Ignored phrases",
    desc: "One phrase per line (case-insensitive)."
  },
  caseSensitive: {
    name: "Case-sensitive matching",
    desc: "Only link text that matches a title or alias with the same letter case."
  },
  firstLinkPerPhrase: {
    name: "First link per phrase",
    desc: "Add at most one wikilink per phrase in each note (first occurrence only)."
  },
  includeGlobs: {
    name: "Include paths (globs)",
    desc: "Only modify notes whose vault path matches one pattern per line (e.g. notes/**). Empty = all notes."
  },
  excludeGlobs: {
    name: "Exclude paths (globs)",
    desc: "Skip notes matching these vault-relative globs (e.g. templates/**)."
  }
};
function readBoolean(record, key) {
  const value = record[key];
  return typeof value === "boolean" ? value : void 0;
}
function readNumber(record, key) {
  const value = record[key];
  return typeof value === "number" && Number.isFinite(value) ? value : void 0;
}
function readString(record, key) {
  const value = record[key];
  return typeof value === "string" ? value : void 0;
}
function parseStoredSettings(data) {
  if (data === null || typeof data !== "object") {
    return {};
  }
  const record = data;
  const parsed = {};
  const keys = [
    "noSelfLinks",
    "useAliases",
    "useHeadings",
    "skipHeadings",
    "minTitleLength",
    "ignorePhrases",
    "caseSensitive",
    "firstLinkPerPhrase",
    "includeGlobs",
    "excludeGlobs"
  ];
  for (const key of keys) {
    if (key === "minTitleLength") {
      const minTitleLength = readNumber(record, key);
      if (minTitleLength !== void 0)
        parsed.minTitleLength = minTitleLength;
    } else if (key === "ignorePhrases" || key === "includeGlobs" || key === "excludeGlobs") {
      const text = readString(record, key);
      if (text !== void 0)
        parsed[key] = text;
    } else {
      const flag = readBoolean(record, key);
      if (flag !== void 0)
        parsed[key] = flag;
    }
  }
  return parsed;
}
function mergeSettings(stored) {
  return { ...DEFAULT_SETTINGS, ...stored };
}
function applySettingValue(settings, key, value) {
  switch (key) {
    case "noSelfLinks":
      if (typeof value === "boolean")
        settings.noSelfLinks = value;
      break;
    case "useAliases":
      if (typeof value === "boolean")
        settings.useAliases = value;
      break;
    case "useHeadings":
      if (typeof value === "boolean")
        settings.useHeadings = value;
      break;
    case "skipHeadings":
      if (typeof value === "boolean")
        settings.skipHeadings = value;
      break;
    case "minTitleLength":
      if (typeof value === "number" && Number.isFinite(value)) {
        settings.minTitleLength = value;
      }
      break;
    case "ignorePhrases":
    case "includeGlobs":
    case "excludeGlobs":
      if (typeof value === "string")
        settings[key] = value;
      break;
    case "caseSensitive":
      if (typeof value === "boolean")
        settings.caseSensitive = value;
      break;
    case "firstLinkPerPhrase":
      if (typeof value === "boolean")
        settings.firstLinkPerPhrase = value;
      break;
    default:
      break;
  }
}

// src/settings-tab.ts
var import_obsidian2 = require("obsidian");
var LinkerSettingTab = class extends import_obsidian2.PluginSettingTab {
  constructor(app, vaultPlugin) {
    super(app, vaultPlugin);
    this.vaultPlugin = vaultPlugin;
  }
  getSettingDefinitions() {
    return [
      {
        name: SETTING_COPY.noSelfLinks.name,
        desc: SETTING_COPY.noSelfLinks.desc,
        control: { type: "toggle", key: "noSelfLinks", defaultValue: true }
      },
      {
        name: SETTING_COPY.useAliases.name,
        desc: SETTING_COPY.useAliases.desc,
        control: { type: "toggle", key: "useAliases", defaultValue: true }
      },
      {
        name: SETTING_COPY.useHeadings.name,
        desc: SETTING_COPY.useHeadings.desc,
        control: { type: "toggle", key: "useHeadings", defaultValue: false }
      },
      {
        name: SETTING_COPY.skipHeadings.name,
        desc: SETTING_COPY.skipHeadings.desc,
        control: { type: "toggle", key: "skipHeadings", defaultValue: true }
      },
      {
        name: SETTING_COPY.minTitleLength.name,
        desc: SETTING_COPY.minTitleLength.desc,
        control: {
          type: "number",
          key: "minTitleLength",
          defaultValue: 1,
          placeholder: "1"
        }
      },
      {
        name: SETTING_COPY.ignorePhrases.name,
        desc: SETTING_COPY.ignorePhrases.desc,
        control: {
          type: "textarea",
          key: "ignorePhrases",
          defaultValue: "README"
        }
      },
      {
        name: SETTING_COPY.caseSensitive.name,
        desc: SETTING_COPY.caseSensitive.desc,
        control: { type: "toggle", key: "caseSensitive", defaultValue: false }
      },
      {
        name: SETTING_COPY.firstLinkPerPhrase.name,
        desc: SETTING_COPY.firstLinkPerPhrase.desc,
        control: { type: "toggle", key: "firstLinkPerPhrase", defaultValue: false }
      },
      {
        name: SETTING_COPY.includeGlobs.name,
        desc: SETTING_COPY.includeGlobs.desc,
        control: { type: "textarea", key: "includeGlobs", defaultValue: "" }
      },
      {
        name: SETTING_COPY.excludeGlobs.name,
        desc: SETTING_COPY.excludeGlobs.desc,
        control: { type: "textarea", key: "excludeGlobs", defaultValue: "" }
      }
    ];
  }
  async setControlValue(key, value) {
    applySettingValue(this.vaultPlugin.settings, key, value);
    await this.vaultPlugin.saveSettings();
  }
  display() {
    const { containerEl } = this;
    const settings = this.vaultPlugin.settings;
    containerEl.empty();
    new import_obsidian2.Setting(containerEl).setName(SETTING_COPY.noSelfLinks.name).setDesc(SETTING_COPY.noSelfLinks.desc).addToggle((toggle) => {
      toggle.setValue(settings.noSelfLinks);
      toggle.onChange((value) => {
        void this.setControlValue("noSelfLinks", value);
      });
    });
    new import_obsidian2.Setting(containerEl).setName(SETTING_COPY.useAliases.name).setDesc(SETTING_COPY.useAliases.desc).addToggle((toggle) => {
      toggle.setValue(settings.useAliases);
      toggle.onChange((value) => {
        void this.setControlValue("useAliases", value);
      });
    });
    new import_obsidian2.Setting(containerEl).setName(SETTING_COPY.useHeadings.name).setDesc(SETTING_COPY.useHeadings.desc).addToggle((toggle) => {
      toggle.setValue(settings.useHeadings);
      toggle.onChange((value) => {
        void this.setControlValue("useHeadings", value);
      });
    });
    new import_obsidian2.Setting(containerEl).setName(SETTING_COPY.skipHeadings.name).setDesc(SETTING_COPY.skipHeadings.desc).addToggle((toggle) => {
      toggle.setValue(settings.skipHeadings);
      toggle.onChange((value) => {
        void this.setControlValue("skipHeadings", value);
      });
    });
    new import_obsidian2.Setting(containerEl).setName(SETTING_COPY.minTitleLength.name).setDesc(SETTING_COPY.minTitleLength.desc).addText((text) => {
      text.setPlaceholder("1");
      text.setValue(String(settings.minTitleLength));
      text.onChange((value) => {
        const parsed = Number.parseInt(value, 10);
        void this.setControlValue(
          "minTitleLength",
          Number.isFinite(parsed) ? parsed : 1
        );
      });
    });
    new import_obsidian2.Setting(containerEl).setName(SETTING_COPY.ignorePhrases.name).setDesc(SETTING_COPY.ignorePhrases.desc).addTextArea((text) => {
      text.setValue(settings.ignorePhrases);
      text.onChange((value) => {
        void this.setControlValue("ignorePhrases", value);
      });
    });
    new import_obsidian2.Setting(containerEl).setName(SETTING_COPY.caseSensitive.name).setDesc(SETTING_COPY.caseSensitive.desc).addToggle((toggle) => {
      toggle.setValue(settings.caseSensitive);
      toggle.onChange((value) => {
        void this.setControlValue("caseSensitive", value);
      });
    });
    new import_obsidian2.Setting(containerEl).setName(SETTING_COPY.firstLinkPerPhrase.name).setDesc(SETTING_COPY.firstLinkPerPhrase.desc).addToggle((toggle) => {
      toggle.setValue(settings.firstLinkPerPhrase);
      toggle.onChange((value) => {
        void this.setControlValue("firstLinkPerPhrase", value);
      });
    });
    new import_obsidian2.Setting(containerEl).setName(SETTING_COPY.includeGlobs.name).setDesc(SETTING_COPY.includeGlobs.desc).addTextArea((text) => {
      text.setValue(settings.includeGlobs);
      text.onChange((value) => {
        void this.setControlValue("includeGlobs", value);
      });
    });
    new import_obsidian2.Setting(containerEl).setName(SETTING_COPY.excludeGlobs.name).setDesc(SETTING_COPY.excludeGlobs.desc).addTextArea((text) => {
      text.setValue(settings.excludeGlobs);
      text.onChange((value) => {
        void this.setControlValue("excludeGlobs", value);
      });
    });
  }
};

// src/globs.ts
function globPatternToRegExp(pattern) {
  const normalized = pattern.replace(/\\/g, "/");
  let regex = "^";
  for (let i = 0; i < normalized.length; i++) {
    const char = normalized[i];
    if (char === "*") {
      if (normalized[i + 1] === "*") {
        regex += ".*";
        i += 1;
      } else {
        regex += "[^/]*";
      }
    } else if (char === "?") {
      regex += ".";
    } else if (char === "[") {
      const close = normalized.indexOf("]", i);
      if (close > i) {
        regex += normalized.slice(i, close + 1);
        i = close;
      } else {
        regex += "\\[";
      }
    } else if ("\\^$+.()|{}".includes(char)) {
      regex += `\\${char}`;
    } else {
      regex += char;
    }
  }
  regex += "$";
  return new RegExp(regex);
}
function parseGlobLines(text) {
  return text.split("\n").map((line) => line.trim()).filter((line) => line.length > 0 && !line.startsWith("#"));
}
function pathMatchesGlobs(vaultRelativePath, includeGlobs, excludeGlobs) {
  const path = vaultRelativePath.replace(/\\/g, "/");
  if (excludeGlobs.some((pattern) => globPatternToRegExp(pattern).test(path))) {
    return false;
  }
  if (includeGlobs.length === 0) {
    return true;
  }
  return includeGlobs.some((pattern) => globPatternToRegExp(pattern).test(path));
}

// src/vault-io.ts
async function loadMarkdownPayload(vault, filter) {
  var _a, _b;
  const allFiles = vault.getMarkdownFiles();
  const includeGlobs = (_a = filter == null ? void 0 : filter.includeGlobs) != null ? _a : [];
  const excludeGlobs = (_b = filter == null ? void 0 : filter.excludeGlobs) != null ? _b : [];
  const files = allFiles.filter(
    (file) => pathMatchesGlobs(file.path, includeGlobs, excludeGlobs)
  );
  const filePayload = [];
  for (const file of files) {
    const content = await vault.read(file);
    filePayload.push({ path: file.path, content });
  }
  return { files, filePayload };
}
function contentForPath(filePayload, path) {
  var _a;
  const entry = filePayload.find((item) => item.path === path);
  return (_a = entry == null ? void 0 : entry.content) != null ? _a : "";
}

// src/main.ts
var VaultLinkerPlugin = class extends import_obsidian3.Plugin {
  constructor() {
    super(...arguments);
    this.settings = mergeSettings({});
  }
  async onload() {
    await this.loadSettings();
    this.addCommand({
      id: "link-vault-titles",
      name: "Link note titles in vault",
      callback: () => {
        this.promptAndRun("link", false);
      }
    });
    this.addCommand({
      id: "link-vault-titles-dry-run",
      name: "Preview title links (dry run)",
      callback: () => {
        this.promptAndRun("link", true);
      }
    });
    this.addCommand({
      id: "audit-vault-links",
      name: "Audit vault links",
      callback: () => {
        void this.runAudit();
      }
    });
    this.addCommand({
      id: "unlink-vault-titles",
      name: "Remove managed title links",
      callback: () => {
        this.promptAndRun("unlink", false);
      }
    });
    this.addCommand({
      id: "unlink-vault-titles-dry-run",
      name: "Preview removing managed links",
      callback: () => {
        this.promptAndRun("unlink", true);
      }
    });
    this.addSettingTab(new LinkerSettingTab(this.app, this));
  }
  async loadSettings() {
    const stored = await this.loadData();
    this.settings = mergeSettings(parseStoredSettings(stored));
  }
  async saveSettings() {
    await this.saveData(this.settings);
  }
  fileFilter() {
    return {
      includeGlobs: parseGlobLines(this.settings.includeGlobs),
      excludeGlobs: parseGlobLines(this.settings.excludeGlobs)
    };
  }
  linkerOptions() {
    return {
      noSelfLinks: this.settings.noSelfLinks,
      useAliases: this.settings.useAliases,
      useHeadings: this.settings.useHeadings,
      skipHeadings: this.settings.skipHeadings,
      minTitleLength: this.settings.minTitleLength,
      caseSensitive: this.settings.caseSensitive,
      firstLinkPerPhrase: this.settings.firstLinkPerPhrase,
      ignorePhrases: new Set(
        this.settings.ignorePhrases.split("\n").map((line) => line.trim().toLocaleLowerCase()).filter(Boolean)
      )
    };
  }
  promptAndRun(mode, dryRun) {
    const modal = new ConfirmLinkerModal(this.app, mode, dryRun, () => {
      if (mode === "link") {
        void this.runLinker(dryRun);
      } else {
        void this.runUnlink(dryRun);
      }
    });
    modal.open();
  }
  async runLinker(dryRun) {
    const filter = this.fileFilter();
    const { files, filePayload } = await loadMarkdownPayload(this.app.vault, filter);
    const options = this.linkerOptions();
    const phrases = buildPhrases(filePayload, options);
    let totalLinks = 0;
    let editedFiles = 0;
    for (const file of files) {
      const original = contentForPath(filePayload, file.path);
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
      if (!dryRun) {
        await this.app.vault.modify(file, content);
      }
    }
    const summary = dryRun ? `Would add ${String(totalLinks)} links in ${String(editedFiles)} notes.` : `Added ${String(totalLinks)} links in ${String(editedFiles)} notes.`;
    new import_obsidian3.Notice(summary);
  }
  async runUnlink(dryRun) {
    const filter = this.fileFilter();
    const { files, filePayload } = await loadMarkdownPayload(this.app.vault, filter);
    const options = this.linkerOptions();
    const phrases = buildPhrases(filePayload, options);
    const managedKeys = buildManagedLinkKeys(phrases);
    let totalRemoved = 0;
    let editedFiles = 0;
    for (const file of files) {
      const original = contentForPath(filePayload, file.path);
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
      if (!dryRun) {
        await this.app.vault.modify(file, content);
      }
    }
    const summary = dryRun ? `Would remove ${String(totalRemoved)} links in ${String(editedFiles)} notes.` : `Removed ${String(totalRemoved)} links in ${String(editedFiles)} notes.`;
    new import_obsidian3.Notice(summary);
  }
  async runAudit() {
    const filter = this.fileFilter();
    const { filePayload } = await loadMarkdownPayload(this.app.vault, filter);
    const report = auditVault(filePayload, this.linkerOptions());
    const modal = new AuditReportModal(this.app, report);
    modal.open();
  }
};
