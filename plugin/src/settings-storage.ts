import { LinkerPluginSettings, SettingsKey } from "./types";

export const DEFAULT_SETTINGS: LinkerPluginSettings = {
  noSelfLinks: true,
  useAliases: true,
  useHeadings: false,
  skipHeadings: true,
  minTitleLength: 1,
  ignorePhrases: "README",
  caseSensitive: false,
  firstLinkPerPhrase: false,
  includeGlobs: "",
  excludeGlobs: "",
};

export const SETTING_COPY: Record<SettingsKey, { name: string; desc: string }> = {
  noSelfLinks: {
    name: "No self links",
    desc: "Do not link a note title inside its own file.",
  },
  useAliases: {
    name: "Use aliases",
    desc: "Use YAML alias / aliases fields from front matter.",
  },
  useHeadings: {
    name: "Use h1 headings",
    desc: "Also treat each note's first # heading as a link phrase.",
  },
  skipHeadings: {
    name: "Skip headings",
    desc: "Do not add links on Markdown heading lines.",
  },
  minTitleLength: {
    name: "Minimum title length",
    desc: "Ignore link phrases shorter than this length.",
  },
  ignorePhrases: {
    name: "Ignored phrases",
    desc: "One phrase per line (case-insensitive).",
  },
  caseSensitive: {
    name: "Case-sensitive matching",
    desc: "Only link text that matches a title or alias with the same letter case.",
  },
  firstLinkPerPhrase: {
    name: "First link per phrase",
    desc: "Add at most one wikilink per phrase in each note (first occurrence only).",
  },
  includeGlobs: {
    name: "Include paths (globs)",
    desc: "Only modify notes whose vault path matches one pattern per line (e.g. notes/**). Empty = all notes.",
  },
  excludeGlobs: {
    name: "Exclude paths (globs)",
    desc: "Skip notes matching these vault-relative globs (e.g. templates/**).",
  },
};

function readBoolean(record: Record<string, unknown>, key: SettingsKey): boolean | undefined {
  const value = record[key];
  return typeof value === "boolean" ? value : undefined;
}

function readNumber(record: Record<string, unknown>, key: SettingsKey): number | undefined {
  const value = record[key];
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function readString(record: Record<string, unknown>, key: SettingsKey): string | undefined {
  const value = record[key];
  return typeof value === "string" ? value : undefined;
}

export function parseStoredSettings(data: unknown): Partial<LinkerPluginSettings> {
  if (data === null || typeof data !== "object") {
    return {};
  }
  const record = data as Record<string, unknown>;
  const parsed: Partial<LinkerPluginSettings> = {};
  const keys: SettingsKey[] = [
    "noSelfLinks",
    "useAliases",
    "useHeadings",
    "skipHeadings",
    "minTitleLength",
    "ignorePhrases",
    "caseSensitive",
    "firstLinkPerPhrase",
    "includeGlobs",
    "excludeGlobs",
  ];
  for (const key of keys) {
    if (key === "minTitleLength") {
      const minTitleLength = readNumber(record, key);
      if (minTitleLength !== undefined) parsed.minTitleLength = minTitleLength;
    } else if (
      key === "ignorePhrases" ||
      key === "includeGlobs" ||
      key === "excludeGlobs"
    ) {
      const text = readString(record, key);
      if (text !== undefined) parsed[key] = text;
    } else {
      const flag = readBoolean(record, key);
      if (flag !== undefined) parsed[key] = flag;
    }
  }
  return parsed;
}

export function mergeSettings(
  stored: Partial<LinkerPluginSettings>
): LinkerPluginSettings {
  return { ...DEFAULT_SETTINGS, ...stored };
}

export function applySettingValue(
  settings: LinkerPluginSettings,
  key: string,
  value: unknown
): void {
  switch (key) {
    case "noSelfLinks":
      if (typeof value === "boolean") settings.noSelfLinks = value;
      break;
    case "useAliases":
      if (typeof value === "boolean") settings.useAliases = value;
      break;
    case "useHeadings":
      if (typeof value === "boolean") settings.useHeadings = value;
      break;
    case "skipHeadings":
      if (typeof value === "boolean") settings.skipHeadings = value;
      break;
    case "minTitleLength":
      if (typeof value === "number" && Number.isFinite(value)) {
        settings.minTitleLength = value;
      }
      break;
    case "ignorePhrases":
    case "includeGlobs":
    case "excludeGlobs":
      if (typeof value === "string") settings[key] = value;
      break;
    case "caseSensitive":
      if (typeof value === "boolean") settings.caseSensitive = value;
      break;
    case "firstLinkPerPhrase":
      if (typeof value === "boolean") settings.firstLinkPerPhrase = value;
      break;
    default:
      break;
  }
}
