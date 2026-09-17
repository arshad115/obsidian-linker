import { LinkerPluginSettings, SettingsKey } from "./types";

export const DEFAULT_SETTINGS: LinkerPluginSettings = {
  noSelfLinks: true,
  useAliases: true,
  useHeadings: false,
  skipHeadings: true,
  minTitleLength: 1,
  ignorePhrases: "README",
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
  const noSelfLinks = readBoolean(record, "noSelfLinks");
  if (noSelfLinks !== undefined) parsed.noSelfLinks = noSelfLinks;
  const useAliases = readBoolean(record, "useAliases");
  if (useAliases !== undefined) parsed.useAliases = useAliases;
  const useHeadings = readBoolean(record, "useHeadings");
  if (useHeadings !== undefined) parsed.useHeadings = useHeadings;
  const skipHeadings = readBoolean(record, "skipHeadings");
  if (skipHeadings !== undefined) parsed.skipHeadings = skipHeadings;
  const minTitleLength = readNumber(record, "minTitleLength");
  if (minTitleLength !== undefined) parsed.minTitleLength = minTitleLength;
  const ignorePhrases = readString(record, "ignorePhrases");
  if (ignorePhrases !== undefined) parsed.ignorePhrases = ignorePhrases;
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
      if (typeof value === "string") settings.ignorePhrases = value;
      break;
    default:
      break;
  }
}
