import { App, PluginSettingTab, Setting, SettingDefinitionItem } from "obsidian";
import {
  applySettingValue,
  SETTING_COPY,
} from "./settings-storage";
import { SettingsKey, VaultLinkerPluginLike } from "./types";

export class LinkerSettingTab extends PluginSettingTab {
  private readonly vaultPlugin: VaultLinkerPluginLike;

  constructor(app: App, vaultPlugin: VaultLinkerPluginLike) {
    super(app, vaultPlugin);
    this.vaultPlugin = vaultPlugin;
  }

  getSettingDefinitions(): SettingDefinitionItem<SettingsKey>[] {
    return [
      {
        name: SETTING_COPY.noSelfLinks.name,
        desc: SETTING_COPY.noSelfLinks.desc,
        control: { type: "toggle", key: "noSelfLinks", defaultValue: true },
      },
      {
        name: SETTING_COPY.useAliases.name,
        desc: SETTING_COPY.useAliases.desc,
        control: { type: "toggle", key: "useAliases", defaultValue: true },
      },
      {
        name: SETTING_COPY.useHeadings.name,
        desc: SETTING_COPY.useHeadings.desc,
        control: { type: "toggle", key: "useHeadings", defaultValue: false },
      },
      {
        name: SETTING_COPY.skipHeadings.name,
        desc: SETTING_COPY.skipHeadings.desc,
        control: { type: "toggle", key: "skipHeadings", defaultValue: true },
      },
      {
        name: SETTING_COPY.minTitleLength.name,
        desc: SETTING_COPY.minTitleLength.desc,
        control: {
          type: "number",
          key: "minTitleLength",
          defaultValue: 1,
          placeholder: "1",
        },
      },
      {
        name: SETTING_COPY.ignorePhrases.name,
        desc: SETTING_COPY.ignorePhrases.desc,
        control: {
          type: "textarea",
          key: "ignorePhrases",
          defaultValue: "README",
        },
      },
    ];
  }

  async setControlValue(key: string, value: unknown): Promise<void> {
    applySettingValue(this.vaultPlugin.settings, key, value);
    await this.vaultPlugin.saveSettings();
  }

  display(): void {
    const { containerEl } = this;
    const settings = this.vaultPlugin.settings;
    containerEl.empty();

    new Setting(containerEl)
      .setName(SETTING_COPY.noSelfLinks.name)
      .setDesc(SETTING_COPY.noSelfLinks.desc)
      .addToggle((toggle) => {
        toggle.setValue(settings.noSelfLinks);
        toggle.onChange((value: boolean) => {
          void this.setControlValue("noSelfLinks", value);
        });
      });

    new Setting(containerEl)
      .setName(SETTING_COPY.useAliases.name)
      .setDesc(SETTING_COPY.useAliases.desc)
      .addToggle((toggle) => {
        toggle.setValue(settings.useAliases);
        toggle.onChange((value: boolean) => {
          void this.setControlValue("useAliases", value);
        });
      });

    new Setting(containerEl)
      .setName(SETTING_COPY.useHeadings.name)
      .setDesc(SETTING_COPY.useHeadings.desc)
      .addToggle((toggle) => {
        toggle.setValue(settings.useHeadings);
        toggle.onChange((value: boolean) => {
          void this.setControlValue("useHeadings", value);
        });
      });

    new Setting(containerEl)
      .setName(SETTING_COPY.skipHeadings.name)
      .setDesc(SETTING_COPY.skipHeadings.desc)
      .addToggle((toggle) => {
        toggle.setValue(settings.skipHeadings);
        toggle.onChange((value: boolean) => {
          void this.setControlValue("skipHeadings", value);
        });
      });

    new Setting(containerEl)
      .setName(SETTING_COPY.minTitleLength.name)
      .setDesc(SETTING_COPY.minTitleLength.desc)
      .addText((text) => {
        text.setPlaceholder("1");
        text.setValue(String(settings.minTitleLength));
        text.onChange((value: string) => {
          const parsed = Number.parseInt(value, 10);
          void this.setControlValue(
            "minTitleLength",
            Number.isFinite(parsed) ? parsed : 1
          );
        });
      });

    new Setting(containerEl)
      .setName(SETTING_COPY.ignorePhrases.name)
      .setDesc(SETTING_COPY.ignorePhrases.desc)
      .addTextArea((text) => {
        text.setValue(settings.ignorePhrases);
        text.onChange((value: string) => {
          void this.setControlValue("ignorePhrases", value);
        });
      });
  }
}
