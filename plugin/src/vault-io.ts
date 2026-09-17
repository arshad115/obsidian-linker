import { TFile, Vault } from "obsidian";
import { FilePayload } from "./types";

export async function loadMarkdownPayload(
  vault: Vault
): Promise<{ files: TFile[]; filePayload: FilePayload[] }> {
  const files: TFile[] = vault.getMarkdownFiles();
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
