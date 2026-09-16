export interface LinkPhrase {
  phrase: string;
  canonical: string;
  sourcePath: string;
}

export interface LinkerOptions {
  noSelfLinks: boolean;
  useAliases: boolean;
  skipHeadings: boolean;
  ignorePhrases: Set<string>;
  minTitleLength: number;
}

export interface LinkerResult {
  content: string;
  linksAdded: number;
}

const CODE_BLOCK = /```[\s\S]*?```/g;
const INLINE_CODE = /`[^`]*`/g;
const EMBED = /!\[\[(?:[^\]|]+\|)?[^\]]+\]\]/g;
const MD_LINK = /\[[^\]]+\]\([^)]+\)/g;
const WIKILINK = /(?<!!)\[\[(?:[^\]|]+\|)?[^\]]+\]\]/g;
const METADATA = /---\s*\n([\s\S]*?)\n\s*---/;
const HEADING_LINE = /^(\s{0,3}#{1,6}\s.+)$/gm;

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function formatWikilink(canonical: string, matched: string): string {
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

function phraseIgnored(phrase: string, options: LinkerOptions): boolean {
  const trimmed = phrase.trim();
  if (!trimmed || trimmed.length < options.minTitleLength) return true;
  return options.ignorePhrases.has(trimmed.toLocaleLowerCase());
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
  }

  return Array.from(phraseMap.values()).sort(
    (a, b) => b.phrase.length - a.phrase.length
  );
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

export function linkContent(
  content: string,
  phrases: LinkPhrase[],
  sourcePath: string,
  options: LinkerOptions
): LinkerResult {
  let linksAdded = 0;
  let working = content;
  const metadataMatch = METADATA.exec(working);
  const metadata = metadataMatch?.[0] ?? "";
  if (metadata) working = working.replace(metadata, "<METADATA_SECTION>");

  let [protectedContent, stashed] = protect(working, options.skipHeadings);
  const withoutLinks = protectedContent.replace(WIKILINK, "");

  for (const entry of phrases) {
    if (options.noSelfLinks && entry.sourcePath === sourcePath) continue;
    if (!withoutLinks.toLocaleLowerCase().includes(entry.phrase.toLocaleLowerCase())) {
      continue;
    }
    const pattern = new RegExp(
      `(?<!\\[\\[)\\b${escapeRegExp(entry.phrase)}\\b(?!\\]\\])`,
      "gi"
    );
    protectedContent = protectedContent.replace(pattern, (matched) => {
      linksAdded += 1;
      return formatWikilink(entry.canonical, matched);
    });
  }

  let restored = unprotect(protectedContent, stashed);
  if (metadata) restored = restored.replace("<METADATA_SECTION>", metadata);
  return { content: restored, linksAdded };
}
