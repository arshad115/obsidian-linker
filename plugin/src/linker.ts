export interface LinkPhrase {
  phrase: string;
  canonical: string;
  sourcePath: string;
}

export interface LinkerOptions {
  noSelfLinks: boolean;
  useAliases: boolean;
  useHeadings: boolean;
  skipHeadings: boolean;
  ignorePhrases: Set<string>;
  minTitleLength: number;
}

export interface LinkerResult {
  content: string;
  linksAdded: number;
}

export interface UnlinkChange {
  line: number;
  wikilink: string;
  restoredText: string;
}

export interface UnlinkResult {
  content: string;
  linksRemoved: number;
  changes: UnlinkChange[];
}

export interface BrokenLink {
  filePath: string;
  line: number;
  target: string;
  wikilink: string;
}

export interface AuditReport {
  pendingLinks: number;
  pendingFiles: number;
  brokenLinks: BrokenLink[];
  zeroBacklinkNotes: string[];
  topLinkedTitles: { title: string; count: number }[];
}

const CODE_BLOCK = /```[\s\S]*?```/g;
const INLINE_CODE = /`[^`]*`/g;
const EMBED = /!\[\[(?:[^\]|]+\|)?[^\]]+\]\]/g;
const MD_LINK = /\[[^\]]+\]\([^)]+\)/g;
const WIKILINK = /(?<!!)\[\[(?:[^\]|]+\|)?[^\]]+\]\]/g;
const WIKILINK_CAPTURE = /(?<!!)\[\[([^\]]+)\]\]/g;
const METADATA = /---\s*\n([\s\S]*?)\n\s*---/;
const HEADING_LINE = /^(\s{0,3}#{1,6}\s.+)$/gm;
const FIRST_H1 = /^#\s+(.+?)\s*$/m;

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function formatWikilink(canonical: string, matched: string): string {
  if (matched.toLocaleLowerCase() === canonical.toLocaleLowerCase()) {
    return `[[${matched}]]`;
  }
  return `[[${canonical}|${matched}]]`;
}

function stripYamlScalar(value: string): string {
  const trimmed = value.trim();
  if (
    trimmed.length >= 2 &&
    ((trimmed.startsWith('"') && trimmed.endsWith('"')) ||
      (trimmed.startsWith("'") && trimmed.endsWith("'")))
  ) {
    return trimmed.slice(1, -1);
  }
  return trimmed;
}

function parseAliases(metadata: string): string[] {
  if (!metadata) return [];
  let inner = metadata.trim();
  if (inner.startsWith("---")) inner = inner.slice(3);
  if (inner.endsWith("---")) inner = inner.slice(0, -3);
  const aliases: string[] = [];
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
        if (part.trim()) aliases.push(stripYamlScalar(part));
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

function parseFirstH1(body: string): string | null {
  const match = body.match(FIRST_H1);
  return match ? match[1].trim() : null;
}

function phraseIgnored(phrase: string, options: LinkerOptions): boolean {
  const trimmed = phrase.trim();
  if (!trimmed || trimmed.length < options.minTitleLength) return true;
  return options.ignorePhrases.has(trimmed.toLocaleLowerCase());
}

export function parseWikilinkInner(inner: string): [string, string] {
  if (inner.includes("|")) {
    const [left, display] = inner.split("|", 2);
    const target = left.split("#", 1)[0].trim();
    return [target, display.trim()];
  }
  const target = inner.split("#", 1)[0].trim();
  return [target, target];
}

export function buildManagedLinkKeys(phrases: LinkPhrase[]): Map<string, LinkPhrase> {
  const keys = new Map<string, LinkPhrase>();
  for (const entry of phrases) {
    keys.set(
      `${entry.canonical.toLocaleLowerCase()}\0${entry.phrase.toLocaleLowerCase()}`,
      entry
    );
  }
  return keys;
}

export function buildPhrases(
  files: { path: string; content: string }[],
  options: LinkerOptions
): LinkPhrase[] {
  const byTitle = new Map<string, string[]>();
  for (const file of files) {
    const title = file.path.split("/").pop()?.replace(/\.md$/i, "") ?? "";
    const key = title.toLocaleLowerCase();
    const paths = byTitle.get(key) ?? [];
    paths.push(file.path);
    byTitle.set(key, paths);
  }

  const winners = new Map<string, string>();
  for (const [titleLower, paths] of byTitle.entries()) {
    winners.set(titleLower, paths.sort((a, b) => b.length - a.length)[0]);
  }

  const phraseMap = new Map<string, LinkPhrase>();
  const register = (phrase: string, canonical: string, sourcePath: string) => {
    if (phraseIgnored(phrase, options)) return;
    const key = phrase.toLocaleLowerCase();
    phraseMap.set(key, { phrase, canonical, sourcePath });
  };

  for (const file of files) {
    const canonical = file.path.split("/").pop()?.replace(/\.md$/i, "") ?? "";
    const titleLower = canonical.toLocaleLowerCase();
    if (winners.get(titleLower) === file.path) {
      register(canonical, canonical, file.path);
    }

    const metadataMatch = METADATA.exec(file.content);
    const metadata = metadataMatch?.[0] ?? "";
    let body = file.content;
    if (metadata) body = body.replace(metadata, "");

    if (options.useAliases) {
      for (const alias of parseAliases(metadata)) {
        register(alias, canonical, file.path);
      }
    }

    if (options.useHeadings) {
      const heading = parseFirstH1(body);
      if (heading) register(heading, canonical, file.path);
    }
  }

  return Array.from(phraseMap.values()).sort(
    (a, b) => b.phrase.length - a.phrase.length
  );
}

function lineNumberAt(content: string, index: number): number {
  return content.slice(0, index).split("\n").length;
}

function protect(content: string, skipHeadings: boolean): [string, string[]] {
  const parts: string[] = [];
  let index = 0;
  const stash = (pattern: RegExp) => {
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
  if (skipHeadings) stash(HEADING_LINE);
  return [content, parts];
}

function unprotect(content: string, parts: string[]): string {
  return content.replace(/<PH_(\d+)>/g, (_, index) => parts[Number(index)] ?? "");
}

function prepareForLinking(content: string, skipHeadings: boolean): [string, string, string[]] {
  let working = content;
  const metadataMatch = METADATA.exec(working);
  const metadata = metadataMatch?.[0] ?? "";
  if (metadata) working = working.replace(metadata, "<METADATA_SECTION>");

  const [protectedContent, stashed] = protect(working, skipHeadings);
  return [protectedContent, metadata, stashed];
}

function finalizeContent(
  protectedContent: string,
  metadata: string,
  stashed: string[]
): string {
  let restored = unprotect(protectedContent, stashed);
  if (metadata) restored = restored.replace("<METADATA_SECTION>", metadata);
  return restored;
}

export function linkContent(
  content: string,
  phrases: LinkPhrase[],
  sourcePath: string,
  options: LinkerOptions
): LinkerResult {
  let linksAdded = 0;
  const [protectedContent, metadata, stashed] = prepareForLinking(
    content,
    options.skipHeadings
  );
  const withoutLinks = protectedContent.replace(WIKILINK, "");

  let working = protectedContent;
  for (const entry of phrases) {
    if (options.noSelfLinks && entry.sourcePath === sourcePath) continue;
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
    linksAdded,
  };
}

export function unlinkContent(
  content: string,
  managedKeys: Map<string, LinkPhrase>,
  sourcePath: string,
  options: LinkerOptions
): UnlinkResult {
  const changes: UnlinkChange[] = [];
  let removed = 0;
  const [protectedContent, metadata, stashed] = prepareForLinking(
    content,
    options.skipHeadings
  );

  let working = protectedContent;
  working = working.replace(
    WIKILINK_CAPTURE,
    (full, inner: string, offset: number) => {
      const [target, display] = parseWikilinkInner(inner);
      const key = `${target.toLocaleLowerCase()}\0${display.toLocaleLowerCase()}`;
      const entry = managedKeys.get(key);
      if (!entry) return full;
      if (options.noSelfLinks && entry.sourcePath === sourcePath) return full;
      removed += 1;
      changes.push({
        line: lineNumberAt(working, offset),
        wikilink: full,
        restoredText: display,
      });
      return display;
    }
  );

  return {
    content: finalizeContent(working, metadata, stashed),
    linksRemoved: removed,
    changes,
  };
}

export function scanWikilinks(
  content: string,
  skipHeadings: boolean
): { line: number; wikilink: string; target: string }[] {
  const [protectedContent, metadata] = prepareForLinking(content, skipHeadings);
  let working = protectedContent;
  if (metadata) working = working.replace("<METADATA_SECTION>", "");

  const found: { line: number; wikilink: string; target: string }[] = [];
  const wikilinkRe = new RegExp(WIKILINK_CAPTURE.source, WIKILINK_CAPTURE.flags);
  let match: RegExpExecArray | null;
  while ((match = wikilinkRe.exec(working)) !== null) {
    const inner = match[1];
    if (inner === undefined) continue;
    const [target] = parseWikilinkInner(inner);
    found.push({
      line: lineNumberAt(working, match.index),
      wikilink: match[0],
      target,
    });
  }
  return found;
}

export function auditVault(
  files: { path: string; content: string }[],
  options: LinkerOptions
): AuditReport {
  const phrases = buildPhrases(files, options);
  const knownTitles = new Set(
    files.map((file) => file.path.split("/").pop()?.replace(/\.md$/i, "") ?? "").map((t) =>
      t.toLocaleLowerCase()
    )
  );

  let pendingLinks = 0;
  let pendingFiles = 0;
  const backlinkCounts = new Map<string, number>();

  for (const file of files) {
    const { linksAdded } = linkContent(file.content, phrases, file.path, options);
    if (linksAdded > 0) {
      pendingLinks += linksAdded;
      pendingFiles += 1;
    }

    for (const link of scanWikilinks(file.content, options.skipHeadings)) {
      const key = link.target.toLocaleLowerCase();
      backlinkCounts.set(key, (backlinkCounts.get(key) ?? 0) + 1);
    }
  }

  const brokenLinks: BrokenLink[] = [];
  for (const file of files) {
    for (const link of scanWikilinks(file.content, options.skipHeadings)) {
      if (!knownTitles.has(link.target.toLocaleLowerCase())) {
        brokenLinks.push({
          filePath: file.path,
          line: link.line,
          target: link.target,
          wikilink: link.wikilink,
        });
      }
    }
  }

  const titleByLower = new Map<string, string>();
  for (const file of files) {
    const title = file.path.split("/").pop()?.replace(/\.md$/i, "") ?? "";
    titleByLower.set(title.toLocaleLowerCase(), title);
  }

  const zeroBacklinkNotes = Array.from(titleByLower.values())
    .filter((title) => (backlinkCounts.get(title.toLocaleLowerCase()) ?? 0) === 0)
    .sort();

  const topLinkedTitles = Array.from(backlinkCounts.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([key, count]) => ({
      title: titleByLower.get(key) ?? key,
      count,
    }));

  return {
    pendingLinks,
    pendingFiles,
    brokenLinks,
    zeroBacklinkNotes,
    topLinkedTitles,
  };
}
