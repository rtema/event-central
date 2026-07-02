import { Input } from "@mantine/core";
import {
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  type CSSProperties,
  type ReactNode,
} from "react";
import "./CodeEditor.css";
import { highlight, validate, type CodeLanguage } from "./codeSyntax";

export interface CodeEditorProps {
  language: CodeLanguage;
  value: string;
  onChange: (value: string) => void;
  /** Reports the current validation error (or null) whenever it changes. */
  onValidityChange?: (error: string | null) => void;
  label?: ReactNode;
  description?: ReactNode;
  /** External error (e.g. from a form). Shown instead of the live syntax error. */
  error?: ReactNode;
  minRows?: number;
  maxRows?: number;
  disabled?: boolean;
  spellCheck?: boolean;
  id?: string;
}

const LINE_HEIGHT = 1.55 * 13; // must match CodeEditor.css
const PADDING_Y = 10;

/**
 * A lightweight code editor with syntax colouring and live validation, built
 * without any editor dependency. A transparent <textarea> sits over a
 * highlighted <pre>; both share identical typography so the caret aligns with
 * the coloured text. Auto-validation surfaces JSON/CSS/HTML syntax errors as
 * the user types.
 */
export function CodeEditor({
  language,
  value,
  onChange,
  onValidityChange,
  label,
  description,
  error,
  minRows = 6,
  maxRows = 20,
  disabled = false,
  spellCheck = false,
  id,
}: CodeEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const preRef = useRef<HTMLPreElement>(null);

  const highlighted = useMemo(() => highlight(language, value), [language, value]);
  const syntaxError = useMemo(() => validate(language, value), [language, value]);

  useEffect(() => {
    onValidityChange?.(syntaxError);
  }, [syntaxError, onValidityChange]);

  // Autosize the textarea to its content, clamped between minRows and maxRows.
  // When content exceeds the max, the textarea scrolls and the highlight layer
  // is kept in sync.
  const resize = () => {
    const ta = textareaRef.current;
    if (!ta) return;
    const min = minRows * LINE_HEIGHT + PADDING_Y * 2;
    const max = maxRows * LINE_HEIGHT + PADDING_Y * 2;
    ta.style.height = "auto";
    const next = Math.min(Math.max(ta.scrollHeight, min), max);
    ta.style.height = `${next}px`;
    ta.style.overflowY = ta.scrollHeight > max ? "auto" : "hidden";
    syncScroll();
  };

  const syncScroll = () => {
    const ta = textareaRef.current;
    const pre = preRef.current;
    if (!ta || !pre) return;
    pre.scrollTop = ta.scrollTop;
    pre.scrollLeft = ta.scrollLeft;
  };

  useLayoutEffect(resize, [value, minRows, maxRows]);

  useEffect(() => {
    window.addEventListener("resize", resize);
    return () => window.removeEventListener("resize", resize);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key !== "Tab") return;
    e.preventDefault();
    const ta = e.currentTarget;
    const start = ta.selectionStart;
    const end = ta.selectionEnd;
    const next = value.slice(0, start) + "  " + value.slice(end);
    onChange(next);
    requestAnimationFrame(() => {
      ta.selectionStart = ta.selectionEnd = start + 2;
    });
  };

  const shownError = error ?? syntaxError ?? undefined;
  const preStyle: CSSProperties = { whiteSpace: "pre-wrap" };

  return (
    <Input.Wrapper
      label={label}
      description={description}
      error={shownError}
      id={id}
    >
      <div
        className="cm-root"
        data-error={shownError ? "true" : "false"}
        data-disabled={disabled ? "true" : "false"}
      >
        <pre className="cm-pre" aria-hidden="true" ref={preRef} style={preStyle}>
          {/* Trailing newline needs a spacer so the last line stays visible. */}
          <code
            dangerouslySetInnerHTML={{
              __html: highlighted + (value.endsWith("\n") ? "\n" : ""),
            }}
          />
        </pre>
        <textarea
          id={id}
          ref={textareaRef}
          className="cm-textarea"
          value={value}
          disabled={disabled}
          spellCheck={spellCheck}
          autoCapitalize="off"
          autoCorrect="off"
          wrap="soft"
          onChange={(e) => onChange(e.currentTarget.value)}
          onScroll={syncScroll}
          onKeyDown={handleKeyDown}
        />
      </div>
    </Input.Wrapper>
  );
}
