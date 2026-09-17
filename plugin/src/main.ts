import { Notice, Plugin } from "obsidian";
import {
  auditVault,
  buildManagedLinkKeys,
  buildPhrases,
  linkContent,
  LinkerOptions,
  unlinkContent,
} from "./linker";
import { AuditReportModal, ConfirmLinkerModal } from "./modals";
import { mergeSettings, parseStoredSettings } from "./settings-storage";
import { LinkerSettingTab } from "./settings-tab";
import { LinkerPluginSettings } from "./types";
import { contentForPath, loadMarkdownPayload } from "./vault-io";

export default class VaultLinkerPlugin extends Plugin {
  settings: LinkerPluginSettings = mergeSettings({});

  async onload(): Promise<void> {
    await this.loadSettings();

    this.addCommand({
      id: "link-vault-titles",
      name: "Link note titles in vault",
      callback: (): void => {
        this.promptAndRun("link", false);
      },
    });

    this.addCommand({
      id: "link-vault-titles-dry-run",
      name: "Preview title links (dry run)",
      callback: (): void => {
        this.promptAndRun("link", true);
      },
    });

    this.addCommand({
      id: "audit-vault-links",
      name: "Audit vault links",
      callback: (): void => {
        void this.runAudit();
      },
    });

    this.addCommand({
      id: "unlink-vault-titles",
      name: "Remove managed title links",
      callback: (): void => {
        this.promptAndRun("unlink", false);
      },
    });

    this.addCommand({
      id: "unlink-vault-titles-dry-run",
      name: "Preview removing managed links",
      callback: (): void => {
        this.promptAndRun("unlink", true);
      },
    });

    this.addSettingTab(new LinkerSettingTab(this.app, this));
  }

  async loadSettings(): Promise<void> {
    const stored: unknown = await this.loadData();
    this.settings = mergeSettings(parseStoredSettings(stored));
  }

  async saveSettings(): Promise<void> {
    await this.saveData(this.settings);
  }

  linkerOptions(): LinkerOptions {
    return {
      noSelfLinks: this.settings.noSelfLinks,
      useAliases: this.settings.useAliases,
      useHeadings: this.settings.useHeadings,
      skipHeadings: this.settings.skipHeadings,
      minTitleLength: this.settings.minTitleLength,
      ignorePhrases: new Set(
        this.settings.ignorePhrases
          .split("\n")
          .map((line: string) => line.trim().toLocaleLowerCase())
          .filter(Boolean)
      ),
    };
  }

  promptAndRun(mode: "link" | "unlink", dryRun: boolean): void {
    const modal = new ConfirmLinkerModal(this.app, mode, dryRun, () => {
      if (mode === "link") {
        void this.runLinker(dryRun);
      } else {
        void this.runUnlink(dryRun);
      }
    });
    modal.open();
  }

  async runLinker(dryRun: boolean): Promise<void> {
    const { files, filePayload } = await loadMarkdownPayload(this.app.vault);
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
      if (linksAdded === 0) continue;
      totalLinks += linksAdded;
      editedFiles += 1;
      if (!dryRun) {
        await this.app.vault.modify(file, content);
      }
    }

    const summary = dryRun
      ? `Would add ${String(totalLinks)} links in ${String(editedFiles)} notes.`
      : `Added ${String(totalLinks)} links in ${String(editedFiles)} notes.`;
    new Notice(summary);
  }

  async runUnlink(dryRun: boolean): Promise<void> {
    const { files, filePayload } = await loadMarkdownPayload(this.app.vault);
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
      if (linksRemoved === 0) continue;
      totalRemoved += linksRemoved;
      editedFiles += 1;
      if (!dryRun) {
        await this.app.vault.modify(file, content);
      }
    }

    const summary = dryRun
      ? `Would remove ${String(totalRemoved)} links in ${String(editedFiles)} notes.`
      : `Removed ${String(totalRemoved)} links in ${String(editedFiles)} notes.`;
    new Notice(summary);
  }

  async runAudit(): Promise<void> {
    const { filePayload } = await loadMarkdownPayload(this.app.vault);
    const report = auditVault(filePayload, this.linkerOptions());
    const modal = new AuditReportModal(this.app, report);
    modal.open();
  }
}
