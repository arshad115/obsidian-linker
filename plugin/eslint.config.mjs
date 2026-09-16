import obsidianmd from "eslint-plugin-obsidianmd";
import tseslint from "typescript-eslint";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");

export default tseslint.config(
  ...obsidianmd.configs.recommended,
  {
    files: ["plugin/src/**/*.ts"],
    languageOptions: {
      parserOptions: {
        project: "./plugin/tsconfig.json",
        tsconfigRootDir: repoRoot,
      },
    },
  }
);
