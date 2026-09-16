import {
  App,
  Modal,
  Notice,
  Plugin,
  PluginSettingTab,
  Setting,
} from "obsidian";
import {
  auditVault,
  buildManagedLinkKeys,
  buildPhrases,
  linkContent,
  LinkerOptions,
  unlinkContent,
} from "./linker";

interface LinkerPluginSettings {
  noSelfLinks: boolean;
  useAliases: boolean;
  useHeadings: boolean;
  skipHeadings: boolean;
  minTitleLength: number;
  ignorePhrases: string;
}

const DEFAULT_SETTINGS: LinkerPluginSettings = {
  noSelfLinks: true,
  useAliases: true,
  useHeadings: false,
  skipHeadings: true,
  minTitleLength: 1,
  ignorePhrases: "README",
};

export default class ObsidianLinkerPlugin extends Plugin {
  settings: LinkerPluginSettings = DEFAULT_SETTINGS;

  async onload() {
    await this.loadSettings();

    this.addCommand({
      id: "link-vault-titles",
      name: "Link note titles in vault",
      callback: () => this.promptAndRun("link", false),
    });

    this.addCommand({
      id: "link-vault-titles-dry-run",
      name: "Preview title links (dry run)",
      callback: () => this.promptAndRun("link", true),
    });

    this.addCommand({
      id: "audit-vault-links",
      name: "Audit vault links",
      callback: () => this.runAudit(),
    });

    this.addCommand({
      id: "unlink-vault-titles",
      name: "Remove managed title links",
      callback: () => this.promptAndRun("unlink", false),
    });

    this.addCommand({
      id: "unlink-vault-titles-dry-run",
      name: "Preview removing managed links",
      callback: () => this.promptAndRun("unlink", true),
    });

    this.addSettingTab(new LinkerSettingTab(this.app, this));
  }

  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings() {
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
          .map((line) => line.trim().toLocaleLowerCase())
          .filter(Boolean)
      ),
    };
  }

  async loadFilePayload() {
    const files = this.app.vault.getMarkdownFiles();
    const filePayload = [];
    for (const file of files) {
      filePayload.push({
        path: file.path,
        content: await this.app.vault.read(file),
      });
    }
    return { files, filePayload };
  }

  promptAndRun(mode: "link" | "unlink", dryRun: boolean) {
    const modal = new ConfirmLinkerModal(this.app, mode, dryRun, () => {
      if (mode === "link") this.runLinker(dryRun);
      else this.runUnlink(dryRun);
    });
    modal.open();
  }

  async runLinker(dryRun: boolean) {
    const { files, filePayload } = await this.loadFilePayload();
    const options = this.linkerOptions();
    const phrases = buildPhrases(filePayload, options);
    let totalLinks = 0;
    let editedFiles = 0;

    for (const file of files) {
      const original =
        filePayload.find((entry) => entry.path === file.path)?.content ?? "";
      const { content, linksAdded } = linkContent(
        original,
        phrases,
        file.path,
        options
      );
      if (linksAdded === 0) continue;
      totalLinks += linksAdded;
      editedFiles += 1;
      if (!dryRun) await this.app.vault.modify(file, content);
    }

    const summary = dryRun
      ? `Would add ${totalLinks} links in ${editedFiles} notes.`
      : `Added ${totalLinks} links in ${editedFiles} notes.`;
    new Notice(summary);
  }

  async runUnlink(dryRun: boolean) {
    const { files, filePayload } = await this.loadFilePayload();
    const options = this.linkerOptions();
    const phrases = buildPhrases(filePayload, options);
    const managedKeys = buildManagedLinkKeys(phrases);
    let totalRemoved = 0;
    let editedFiles = 0;

    for (const file of files) {
      const original =
        filePayload.find((entry) => entry.path === file.path)?.content ?? "";
      const { content, linksRemoved } = unlinkContent(
        original,
        managedKeys,
        file.path,
        options
      );
      if (linksRemoved === 0) continue;
      totalRemoved += linksRemoved;
      editedFiles += 1;
      if (!dryRun) await this.app.vault.modify(file, content);
    }

    const summary = dryRun
      ? `Would remove ${totalRemoved} links in ${editedFiles} notes.`
      : `Removed ${totalRemoved} links in ${editedFiles} notes.`;
    new Notice(summary);
  }

  async runAudit() {
    const { filePayload } = await this.loadFilePayload();
    const report = auditVault(filePayload, this.linkerOptions());
    const modal = new AuditReportModal(this.app, report);
    modal.open();
  }
}

class ConfirmLinkerModal extends Modal {
  constructor(
    app: App,
    private readonly mode: "link" | "unlink",
    private readonly dryRun: boolean,
    private readonly onConfirm: () => void
  ) {
    super(app);
  }

  onOpen() {
    const { contentEl } = this;
    const titles = {
      link: this.dryRun ? "Preview title links?" : "Link note titles?",
      unlink: this.dryRun ? "Preview removing links?" : "Remove managed links?",
    };
    const bodies = {
      link: this.dryRun
        ? "This will scan your vault and report how many links would be added."
        : "This will modify notes in your vault. Consider a backup or sync commit first.",
      unlink: this.dryRun
        ? "This will report how many managed title/alias links would be removed."
        : "This removes wikilinks created by the same rules as Link note titles. Other links are kept.",
    };
    contentEl.createEl("h2", { text: titles[this.mode] });
    contentEl.createEl("p", { text: bodies[this.mode] });
    contentEl.createEl("button", { text: "Continue", type: "button" }).onclick = () => {
      this.close();
      this.onConfirm();
    };
    contentEl.createEl("button", { text: "Cancel", type: "button" }).onclick = () =>
      this.close();
  }

  onClose() {
    this.contentEl.empty();
  }
}

class AuditReportModal extends Modal {
  constructor(app: App, private readonly report: ReturnType<typeof auditVault>) {
    super(app);
  }

  onOpen() {
    const { contentEl } = this;
    contentEl.createEl("h2", { text: "Vault link audit" });
    contentEl.createEl("p", {
      text: `Pending links: ${this.report.pendingLinks} in ${this.report.pendingFiles} notes`,
    });
    contentEl.createEl("p", {
      text: `Broken wikilinks: ${this.report.brokenLinks.length}`,
    });
    if (this.report.brokenLinks.length > 0) {
      const list = contentEl.createEl("ul");
      for (const broken of this.report.brokenLinks.slice(0, 20)) {
        list.createEl("li", {
          text: `${broken.filePath}:${broken.line}: ${broken.wikilink} → missing '${broken.target}'`,
        });
      }
      if (this.report.brokenLinks.length > 20) {
        list.createEl("li", {
          text: `… and ${this.report.brokenLinks.length - 20} more`,
        });
      }
    }
    contentEl.createEl("p", {
      text: `Notes with zero incoming links: ${this.report.zeroBacklinkNotes.length}`,
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
}

class LinkerSettingTab extends PluginSettingTab {
  plugin: ObsidianLinkerPlugin;

  constructor(app: App, plugin: ObsidianLinkerPlugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display(): void {
    const { containerEl } = this;
    containerEl.empty();
    containerEl.createEl("h2", { text: "Vault Linker" });

    new Setting(containerEl)
      .setName("No self links")
      .setDesc("Do not link a note title inside its own file.")
      .addToggle((toggle) =>
        toggle
          .setValue(this.plugin.settings.noSelfLinks)
          .onChange(async (value) => {
            this.plugin.settings.noSelfLinks = value;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("Use aliases")
      .setDesc("Use YAML alias / aliases fields from front matter.")
      .addToggle((toggle) =>
        toggle
          .setValue(this.plugin.settings.useAliases)
          .onChange(async (value) => {
            this.plugin.settings.useAliases = value;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("Use H1 headings")
      .setDesc("Also treat each note's first # heading as a link phrase.")
      .addToggle((toggle) =>
        toggle
          .setValue(this.plugin.settings.useHeadings)
          .onChange(async (value) => {
            this.plugin.settings.useHeadings = value;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("Skip headings")
      .setDesc("Do not add links on markdown heading lines.")
      .addToggle((toggle) =>
        toggle
          .setValue(this.plugin.settings.skipHeadings)
          .onChange(async (value) => {
            this.plugin.settings.skipHeadings = value;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("Minimum title length")
      .setDesc("Ignore link phrases shorter than this length.")
      .addText((text) =>
        text
          .setPlaceholder("1")
          .setValue(String(this.plugin.settings.minTitleLength))
          .onChange(async (value) => {
            const parsed = Number.parseInt(value, 10);
            this.plugin.settings.minTitleLength = Number.isFinite(parsed) ? parsed : 1;
            await this.plugin.saveSettings();
          })
      );

    new Setting(containerEl)
      .setName("Ignored phrases")
      .setDesc("One phrase per line (case-insensitive).")
      .addTextArea((text) =>
        text
          .setValue(this.plugin.settings.ignorePhrases)
          .onChange(async (value) => {
            this.plugin.settings.ignorePhrases = value;
            await this.plugin.saveSettings();
          })
      );
  }
}
