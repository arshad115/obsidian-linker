import { App, Modal, Setting } from "obsidian";
import { AuditReport } from "./linker";

type LinkRunMode = "link" | "unlink";

export class ConfirmLinkerModal extends Modal {
  constructor(
    app: App,
    private readonly mode: LinkRunMode,
    private readonly dryRun: boolean,
    private readonly onConfirm: () => void
  ) {
    super(app);
  }

  onOpen(): void {
    const { contentEl } = this;
    const titles: Record<LinkRunMode, string> = {
      link: this.dryRun ? "Preview title links?" : "Link note titles?",
      unlink: this.dryRun ? "Preview removing links?" : "Remove managed links?",
    };
    const bodies: Record<LinkRunMode, string> = {
      link: this.dryRun
        ? "This will scan your vault and report how many links would be added."
        : "This will modify notes in your vault. Consider a backup or sync commit first.",
      unlink: this.dryRun
        ? "This will report how many managed title/alias links would be removed."
        : "This removes wikilinks created by the same rules as Link note titles. Other links are kept.",
    };
    new Setting(contentEl).setName(titles[this.mode]).setHeading();
    contentEl.createEl("p", { text: bodies[this.mode] });
    const continueButton = contentEl.createEl("button", {
      text: "Continue",
      type: "button",
    });
    continueButton.onclick = (): void => {
      this.close();
      this.onConfirm();
    };
    const cancelButton = contentEl.createEl("button", {
      text: "Cancel",
      type: "button",
    });
    cancelButton.onclick = (): void => {
      this.close();
    };
  }

  onClose(): void {
    this.contentEl.empty();
  }
}

export class AuditReportModal extends Modal {
  constructor(app: App, private readonly report: AuditReport) {
    super(app);
  }

  onOpen(): void {
    const { contentEl } = this;
    new Setting(contentEl).setName("Vault link audit").setHeading();
    contentEl.createEl("p", {
      text: `Pending links: ${String(this.report.pendingLinks)} in ${String(this.report.pendingFiles)} notes`,
    });
    contentEl.createEl("p", {
      text: `Broken wikilinks: ${String(this.report.brokenLinks.length)}`,
    });
    if (this.report.brokenLinks.length > 0) {
      const list = contentEl.createEl("ul");
      for (const broken of this.report.brokenLinks.slice(0, 20)) {
        list.createEl("li", {
          text: `${broken.filePath}:${String(broken.line)}: ${broken.wikilink} → missing '${broken.target}'`,
        });
      }
      if (this.report.brokenLinks.length > 20) {
        list.createEl("li", {
          text: `… and ${String(this.report.brokenLinks.length - 20)} more`,
        });
      }
    }
    contentEl.createEl("p", {
      text: `Notes with zero incoming links: ${String(this.report.zeroBacklinkNotes.length)}`,
    });
    if (this.report.topLinkedTitles.length > 0) {
      new Setting(contentEl).setName("Most linked titles").setHeading();
      const top = contentEl.createEl("ul");
      for (const entry of this.report.topLinkedTitles) {
        top.createEl("li", { text: `${entry.title} (${String(entry.count)})` });
      }
    }
  }

  onClose(): void {
    this.contentEl.empty();
  }
}
