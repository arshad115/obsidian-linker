import { TFile, Vault } from "obsidian";
import { pathMatchesGlobs } from "./globs";
import { FilePayload, VaultFileFilter } from "./types";

export async function loadMarkdownPayload(
  vault: Vault,
  filter?: VaultFileFilter
): Promise<{ files: TFile[]; filePayload: FilePayload[] }> {
  const allFiles: TFile[] = vault.getMarkdownFiles();
  const includeGlobs = filter?.includeGlobs ?? [];
  const excludeGlobs = filter?.excludeGlobs ?? [];
  const files = allFiles.filter((file) =>
    pathMatchesGlobs(file.path, includeGlobs, excludeGlobs)
  );
  const filePayload: FilePayload[] = [];
  for (const file of files) {
    const content: string = await vault.read(file);
    filePayload.push({ path: file.path, content });
  }
  return { files, filePayload };
}

export function contentForPath(
  filePayload: FilePayload[],
  path: string
): string {
  const entry = filePayload.find((item) => item.path === path);
  return entry?.content ?? "";
}
