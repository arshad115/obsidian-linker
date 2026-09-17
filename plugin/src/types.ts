export interface LinkerPluginSettings {
  noSelfLinks: boolean;
  useAliases: boolean;
  useHeadings: boolean;
  skipHeadings: boolean;
  minTitleLength: number;
  ignorePhrases: string;
  caseSensitive: boolean;
  firstLinkPerPhrase: boolean;
  includeGlobs: string;
  excludeGlobs: string;
}

export type SettingsKey = keyof LinkerPluginSettings;

export interface FilePayload {
  path: string;
  content: string;
}

export interface VaultLinkerPluginLike {
  settings: LinkerPluginSettings;
  saveSettings(): Promise<void>;
}

export interface VaultFileFilter {
  includeGlobs: string[];
  excludeGlobs: string[];
}
