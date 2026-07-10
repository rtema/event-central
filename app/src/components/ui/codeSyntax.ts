/*
 * Tiny, dependency-free syntax highlighting + validation for the three code
 * inputs in the app (JSON user data, and the HTML/CSS template body).
 *
 * `highlight()` returns an HTML string of <span class="tok-…"> tokens that is
 * rendered behind a transparent <textarea> by CodeEditor. `validate()` returns
 * a human-readable error message or null. Both are intentionally forgiving:
 * highlighting never throws, and validation only flags unambiguous syntax
 * problems so valid documents are never falsely rejected.
 */

export type CodeLanguage = "json" | "css" | "html";

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function span(cls: string, text: string): string {
  return `<span class="tok-${cls}">${escapeHtml(text)}</span>`;
}

/* ----------------------------- Highlighting ----------------------------- */

function highlightJson(code: string): string {
  const re =
    /("(?:\\.|[^"\\])*")(\s*:)?|\b(true|false|null)\b|(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)|([{}[\],:])/g;
  let out = "";
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(code)) !== null) {
    out += escapeHtml(code.slice(last, m.index));
    if (m[1] !== undefined) {
      out += span(m[2] ? "key" : "string", m[1]);
      if (m[2]) out += span("punct", m[2]);
    } else if (m[3] !== undefined) {
      out += span("keyword", m[3]);
    } else if (m[4] !== undefined) {
      out += span("number", m[4]);
    } else if (m[5] !== undefined) {
      out += span("punct", m[5]);
    }
    last = re.lastIndex;
  }
  out += escapeHtml(code.slice(last));
  return out;
}

function highlightCss(code: string): string {
  let out = "";
  let i = 0;
  const n = code.length;
  let depth = 0;
  let value = false;

  while (i < n) {
    const c = code[i];
    if (c === "/" && code[i + 1] === "*") {
      const e = code.indexOf("*/", i + 2);
      const end = e < 0 ? n : e + 2;
      out += span("comment", code.slice(i, end));
      i = end;
      continue;
    }
    if (c === '"' || c === "'") {
      let j = i + 1;
      while (j < n && code[j] !== c) {
        if (code[j] === "\\") j++;
        j++;
      }
      j = Math.min(j + 1, n);
      out += span("string", code.slice(i, j));
      i = j;
      continue;
    }
    if (c === "@") {
      const m = /^@[\w-]*/.exec(code.slice(i));
      const tok = m ? m[0] : c;
      out += span("atrule", tok);
      i += tok.length;
      continue;
    }
    if (c === "{") {
      out += span("punct", "{");
      depth++;
      value = false;
      i++;
      continue;
    }
    if (c === "}") {
      out += span("punct", "}");
      if (depth > 0) depth--;
      value = false;
      i++;
      continue;
    }
    if (c === ":" && depth > 0) {
      out += span("punct", ":");
      value = true;
      i++;
      continue;
    }
    if (c === ";") {
      out += span("punct", ";");
      value = false;
      i++;
      continue;
    }
    if (c === "#" && depth > 0 && value) {
      const m = /^#[0-9a-fA-F]{3,8}\b/.exec(code.slice(i));
      if (m) {
        out += span("color", m[0]);
        i += m[0].length;
        continue;
      }
    }
    const isNum =
      /\d/.test(c) ||
      ((c === "-" || c === ".") && /\d/.test(code[i + 1] ?? ""));
    if (isNum) {
      const m = /^-?(?:\d*\.\d+|\d+)(?:[a-zA-Z%]+)?/.exec(code.slice(i));
      if (m) {
        out += span("number", m[0]);
        i += m[0].length;
        continue;
      }
    }
    const w = /^[A-Za-z_-][\w-]*/.exec(code.slice(i));
    if (w) {
      const cls = depth === 0 ? "selector" : value ? "value" : "property";
      out += span(cls, w[0]);
      i += w[0].length;
      continue;
    }
    out += escapeHtml(c);
    i++;
  }
  return out;
}

function highlightAttrs(s: string): string {
  const re =
    /([a-zA-Z_:][\w:.-]*)(\s*=\s*)("[^"]*"|'[^']*'|[^\s"'=<>`]+)?|(\s+)|([^\s]+)/g;
  let out = "";
  let m: RegExpExecArray | null;
  while ((m = re.exec(s)) !== null) {
    if (m[1] !== undefined) {
      out += span("attr", m[1]);
      if (m[2]) out += span("punct", m[2]);
      if (m[3] !== undefined) out += span("string", m[3]);
    } else if (m[4] !== undefined) {
      out += escapeHtml(m[4]);
    } else if (m[5] !== undefined) {
      out += escapeHtml(m[5]);
    }
  }
  return out;
}

function highlightHtml(code: string): string {
  const re =
    /(<!--[\s\S]*?-->)|(<!doctype[^>]*>|<![^>]*>)|({{[\s\S]*?}}|{%[\s\S]*?%}|{#[\s\S]*?#})|(<\/?[a-zA-Z][^>]*>)/gi;
  let out = "";
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(code)) !== null) {
    out += escapeHtml(code.slice(last, m.index));
    if (m[1] !== undefined) {
      out += span("comment", m[1]);
    } else if (m[2] !== undefined) {
      out += span("atrule", m[2]);
    } else if (m[3] !== undefined) {
      out += span("jinja", m[3]);
    } else if (m[4] !== undefined) {
      const tag = m[4];
      const parts = /^(<\/?)([a-zA-Z][\w:-]*)([\s\S]*?)(\/?>)$/.exec(tag);
      if (parts) {
        out +=
          span("punct", parts[1]) +
          span("tag", parts[2]) +
          highlightAttrs(parts[3]) +
          span("punct", parts[4]);
      } else {
        out += escapeHtml(tag);
      }
    }
    last = re.lastIndex;
  }
  out += escapeHtml(code.slice(last));
  return out;
}

export function highlight(language: CodeLanguage, code: string): string {
  try {
    if (language === "json") return highlightJson(code);
    if (language === "css") return highlightCss(code);
    return highlightHtml(code);
  } catch {
    return escapeHtml(code);
  }
}

/* ------------------------------ Validation ------------------------------ */

function validateJson(code: string): string | null {
  try {
    JSON.parse(code);
    return null;
  } catch (e) {
    return (e as Error).message.replace(/^JSON\.parse:\s*/i, "");
  }
}

function validateCss(code: string): string | null {
  let depth = 0;
  let paren = 0;
  for (let i = 0; i < code.length; i++) {
    const c = code[i];
    if (c === "/" && code[i + 1] === "*") {
      const end = code.indexOf("*/", i + 2);
      if (end < 0) return "Unterminated comment (/* … */)";
      i = end + 1;
      continue;
    }
    if (c === '"' || c === "'") {
      let j = i + 1;
      while (j < code.length && code[j] !== c) {
        if (code[j] === "\\") j++;
        j++;
      }
      if (j >= code.length) return "Unterminated string literal";
      i = j;
      continue;
    }
    if (c === "{") depth++;
    else if (c === "}") {
      depth--;
      if (depth < 0) return "Unexpected '}' without a matching '{'";
    } else if (c === "(") paren++;
    else if (c === ")") {
      paren--;
      if (paren < 0) return "Unexpected ')' without a matching '('";
    }
  }
  if (depth > 0)
    return `Missing '}' — ${depth} block${depth > 1 ? "s" : ""} left open`;
  if (paren > 0) return "Unbalanced parentheses";
  return null;
}

function countOccurrences(haystack: string, needle: string): number {
  let count = 0;
  let idx = haystack.indexOf(needle);
  while (idx !== -1) {
    count++;
    idx = haystack.indexOf(needle, idx + needle.length);
  }
  return count;
}

function validateHtml(code: string): string | null {
  const jinja: [string, string, string][] = [
    ["{{", "}}", "{{ }}"],
    ["{%", "%}", "{% %}"],
    ["{#", "#}", "{# #}"],
  ];
  for (const [open, close, label] of jinja) {
    if (countOccurrences(code, open) !== countOccurrences(code, close))
      return `Unbalanced Jinja ${label} delimiters`;
  }
  for (let i = 0; i < code.length; i++) {
    if (code.startsWith("<!--", i)) {
      const end = code.indexOf("-->", i + 4);
      if (end < 0) return "Unterminated comment (<!-- … -->)";
      i = end + 2;
      continue;
    }
    if (code[i] === "<" && /[a-zA-Z/!]/.test(code[i + 1] ?? "")) {
      if (code.indexOf(">", i + 1) < 0)
        return "Unterminated tag — '<' without a closing '>'";
    }
  }
  return null;
}

export function validate(language: CodeLanguage, code: string): string | null {
  if (!code.trim()) return null;
  try {
    if (language === "json") return validateJson(code);
    if (language === "css") return validateCss(code);
    return validateHtml(code);
  } catch {
    return null;
  }
}
