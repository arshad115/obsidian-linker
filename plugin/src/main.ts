import {
  App,
  Modal,
  Notice,
  Plugin,
  PluginSettingTab,
  Setting,
} from "obsidian";
import { buildPhrases, linkContent, LinkerOptions } from "./linker";

interface LinkerPluginSettings {
  noSelfLinks: boolean;
  useAliases: boolean;
  skipHeadings: boolean;
  minTitleLength: number;
  ignorePhrases: string;
}

const DEFAULT_SETTINGS: LinkerPluginSettings = {
  noSelfLinks: true,
  useAliases: true,
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
      callback: () => this.promptAndRun(false),
    });

    this.addCommand({
      id: "link-vault-titles-dry-run",
      name: "Preview title links (dry run)",
      callback: () => this.promptAndRun(true),
    });

    this.addSettingTab(new LinkerSettingTab(this.app, this));
  }

  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings() {
    await this.saveData(this.settings);
  }

  promptAndRun(dryRun: boolean) {
    const modal = new ConfirmLinkerModal(this.app, dryRun, () => this.runLinker(dryRun));
    modal.open();
  }

  async runLinker(dryRun: boolean) {
    const files = this.app.vault.getMarkdownFiles();
    const filePayload = [];
    for (const file of files) {
      filePayload.push({
        path: file.path,
        content: await this.app.vault.read(file),
      });
    }

    const options: LinkerOptions = {
      noSelfLinks: this.settings.noSelfLinks,
      useAliases: this.settings.useAliases,
      skipHeadings: this.settings.skipHeadings,
      minTitleLength: this.settings.minTitleLength,
      ignorePhrases: new Set(
        this.settings.ignorePhrases
          .split("\n")
          .map((line) => line.trim().toLocaleLowerCase())
          .filter(Boolean)
      ),
    };

    const phrases = buildPhrases(filePayload, options);
    let totalLinks = 0;
    let editedFiles = 0;

    for (const file of files) {
      const original = filePayload.find((entry) => entry.path === file.path)?.content ?? "";
      const { content, linksAdded } = linkContent(original, phrases, file.path, options);
      if (linksAdded === 0) continue;
      totalLinks += linksAdded;
      editedFiles += 1;
      if (!dryRun) {
        await this.app.vault.modify(file, content);
      }
    }

    const summary = dryRun
      ? `Would add ${totalLinks} links in ${editedFiles} notes.`
      : `Added ${totalLinks} links in ${editedFiles} notes.`;
    new Notice(summary);
  }
}

class ConfirmLinkerModal extends Modal {
  constructor(
    app: App,
    private readonly dryRun: boolean,
    private readonly onConfirm: () => void
  ) {
    super(app);
  }

  onOpen() {
    const { contentEl } = this;
    contentEl.createEl("h2", {
      text: this.dryRun ? "Preview title links?" : "Link note titles?",
    });
    contentEl.createEl("p", {
      text: this.dryRun
        ? "This will scan your vault and report how many links would be added."
        : "This will modify notes in your vault. Consider a backup or sync commit first.",
    });
    contentEl.createEl("button", { text: "Continue", type: "button" }).onclick = () => {
      this.close();
      this.onConfirm();
    };
    contentEl.createEl("button", { text: "Cancel", type: "button" }).onclick = () => this.close();
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
    containerEl.createEl("h2", { text: "Obsidian Linker" });

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
