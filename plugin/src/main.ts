import {
  App,
  Modal,
  Notice,
  Plugin,
  PluginSettingTab,
  Setting,
  SettingDefinitionItem,
  TFile,
} from "obsidian";
import {
  auditVault,
  AuditReport,
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

type SettingsKey = keyof LinkerPluginSettings;

interface FilePayload {
  path: string;
  content: string;
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
      callback: () => {
        this.promptAndRun("link", false);
      },
    });

    this.addCommand({
      id: "link-vault-titles-dry-run",
      name: "Preview title links (dry run)",
      callback: () => {
        this.promptAndRun("link", true);
      },
    });

    this.addCommand({
      id: "audit-vault-links",
      name: "Audit vault links",
      callback: () => {
        void this.runAudit();
      },
    });

    this.addCommand({
      id: "unlink-vault-titles",
      name: "Remove managed title links",
      callback: () => {
        this.promptAndRun("unlink", false);
      },
    });

    this.addCommand({
      id: "unlink-vault-titles-dry-run",
      name: "Preview removing managed links",
      callback: () => {
        this.promptAndRun("unlink", true);
      },
    });

    this.addSettingTab(new LinkerSettingTab(this.app, this));
  }

  async loadSettings() {
    const data = (await this.loadData()) as Partial<LinkerPluginSettings> | null;
    this.settings = Object.assign({}, DEFAULT_SETTINGS, data ?? {});
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

  async loadFilePayload(): Promise<{ files: TFile[]; filePayload: FilePayload[] }> {
    const files = this.app.vault.getMarkdownFiles();
    const filePayload: FilePayload[] = [];
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
      if (mode === "link") void this.runLinker(dryRun);
      else void this.runUnlink(dryRun);
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
    new Setting(contentEl).setName(titles[this.mode]).setHeading();
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
  constructor(app: App, private readonly report: AuditReport) {
    super(app);
  }

  onOpen() {
    const { contentEl } = this;
    new Setting(contentEl).setName("Vault link audit").setHeading();
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
      new Setting(contentEl).setName("Most linked titles").setHeading();
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

  getSettingDefinitions(): SettingDefinitionItem<SettingsKey>[] {
    return [
      {
        type: "group",
        heading: "Vault Linker",
        items: [
          {
            name: "No self links",
            desc: "Do not link a note title inside its own file.",
            control: { type: "toggle", key: "noSelfLinks", defaultValue: true },
          },
          {
            name: "Use aliases",
            desc: "Use YAML alias / aliases fields from front matter.",
            control: { type: "toggle", key: "useAliases", defaultValue: true },
          },
          {
            name: "Use H1 headings",
            desc: "Also treat each note's first # heading as a link phrase.",
            control: { type: "toggle", key: "useHeadings", defaultValue: false },
          },
          {
            name: "Skip headings",
            desc: "Do not add links on markdown heading lines.",
            control: { type: "toggle", key: "skipHeadings", defaultValue: true },
          },
          {
            name: "Minimum title length",
            desc: "Ignore link phrases shorter than this length.",
            control: {
              type: "number",
              key: "minTitleLength",
              defaultValue: 1,
              placeholder: "1",
            },
          },
          {
            name: "Ignored phrases",
            desc: "One phrase per line (case-insensitive).",
            control: {
              type: "textarea",
              key: "ignorePhrases",
              defaultValue: "README",
            },
          },
        ],
      },
    ];
  }

  setControlValue(key: string, value: unknown): Promise<void> {
    const settings = this.plugin.settings;
    switch (key) {
      case "noSelfLinks":
        settings.noSelfLinks = value as boolean;
        break;
      case "useAliases":
        settings.useAliases = value as boolean;
        break;
      case "useHeadings":
        settings.useHeadings = value as boolean;
        break;
      case "skipHeadings":
        settings.skipHeadings = value as boolean;
        break;
      case "minTitleLength":
        settings.minTitleLength = value as number;
        break;
      case "ignorePhrases":
        settings.ignorePhrases = value as string;
        break;
      default:
        break;
    }
    return this.plugin.saveSettings();
  }

  display(): void {
    const { containerEl } = this;
    containerEl.empty();
    new Setting(containerEl).setName("Vault Linker").setHeading();

    new Setting(containerEl)
      .setName("No self links")
      .setDesc("Do not link a note title inside its own file.")
      .addToggle((toggle) =>
        toggle
          .setValue(this.plugin.settings.noSelfLinks)
          .onChange((value) => {
            void this.setControlValue("noSelfLinks", value);
          })
      );

    new Setting(containerEl)
      .setName("Use aliases")
      .setDesc("Use YAML alias / aliases fields from front matter.")
      .addToggle((toggle) =>
        toggle
          .setValue(this.plugin.settings.useAliases)
          .onChange((value) => {
            void this.setControlValue("useAliases", value);
          })
      );

    new Setting(containerEl)
      .setName("Use H1 headings")
      .setDesc("Also treat each note's first # heading as a link phrase.")
      .addToggle((toggle) =>
        toggle
          .setValue(this.plugin.settings.useHeadings)
          .onChange((value) => {
            void this.setControlValue("useHeadings", value);
          })
      );

    new Setting(containerEl)
      .setName("Skip headings")
      .setDesc("Do not add links on markdown heading lines.")
      .addToggle((toggle) =>
        toggle
          .setValue(this.plugin.settings.skipHeadings)
          .onChange((value) => {
            void this.setControlValue("skipHeadings", value);
          })
      );

    new Setting(containerEl)
      .setName("Minimum title length")
      .setDesc("Ignore link phrases shorter than this length.")
      .addText((text) =>
        text
          .setPlaceholder("1")
          .setValue(String(this.plugin.settings.minTitleLength))
          .onChange((value) => {
            const parsed = Number.parseInt(value, 10);
            void this.setControlValue(
              "minTitleLength",
              Number.isFinite(parsed) ? parsed : 1
            );
          })
      );

    new Setting(containerEl)
      .setName("Ignored phrases")
      .setDesc("One phrase per line (case-insensitive).")
      .addTextArea((text) =>
        text
          .setValue(this.plugin.settings.ignorePhrases)
          .onChange((value) => {
            void this.setControlValue("ignorePhrases", value);
          })
      );
  }
}
