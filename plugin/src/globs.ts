/** Vault-relative path glob matching (fnmatch-style, one pattern per line). */

function globPatternToRegExp(pattern: string): RegExp {
  const normalized = pattern.replace(/\\/g, "/");
  let regex = "^";
  for (let i = 0; i < normalized.length; i++) {
    const char = normalized[i];
    if (char === "*") {
      if (normalized[i + 1] === "*") {
        regex += ".*";
        i += 1;
      } else {
        regex += "[^/]*";
      }
    } else if (char === "?") {
      regex += ".";
    } else if (char === "[") {
      const close = normalized.indexOf("]", i);
      if (close > i) {
        regex += normalized.slice(i, close + 1);
        i = close;
      } else {
        regex += "\\[";
      }
    } else if ("\\^$+.()|{}".includes(char)) {
      regex += `\\${char}`;
    } else {
      regex += char;
    }
  }
  regex += "$";
  return new RegExp(regex);
}

export function parseGlobLines(text: string): string[] {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0 && !line.startsWith("#"));
}

export function pathMatchesGlobs(
  vaultRelativePath: string,
  includeGlobs: string[],
  excludeGlobs: string[]
): boolean {
  const path = vaultRelativePath.replace(/\\/g, "/");
  if (excludeGlobs.some((pattern) => globPatternToRegExp(pattern).test(path))) {
    return false;
  }
  if (includeGlobs.length === 0) {
    return true;
  }
  return includeGlobs.some((pattern) => globPatternToRegExp(pattern).test(path));
}
