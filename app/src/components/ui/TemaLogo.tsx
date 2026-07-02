import type { CSSProperties } from "react";

/**
 * Official TEMA Technologie Marketing AG logo, transcribed from the vector mark
 * used on tema.de. The wordmark renders in TEMA navy (#002f63) and the bracket
 * mark in TEMA cyan (#0f91bd).
 *
 * Pass `variant="mono"` (optionally with `monoColor`) to render the whole mark
 * in a single colour — used on the dark login panel where the logo sits on a
 * navy gradient and needs to read as white.
 */
export interface TemaLogoProps {
  /** Rendered height in pixels. Width scales with the logo's aspect ratio. */
  height?: number;
  /** "color" = brand navy + cyan (default); "mono" = single colour. */
  variant?: "color" | "mono";
  /** Colour used when variant="mono". Defaults to white. */
  monoColor?: string;
  className?: string;
  style?: CSSProperties;
  title?: string;
}

export function TemaLogo({
  height = 40,
  variant = "color",
  monoColor = "#ffffff",
  className,
  style,
  title = "TEMA Technologie Marketing AG",
}: TemaLogoProps) {
  const wordmark = variant === "mono" ? monoColor : "#002f63";
  const mark = variant === "mono" ? monoColor : "#0f91bd";
  const aspect = 119.08 / 63.78;

  return (
    <svg
      viewBox="0 0 119.08 63.78"
      role="img"
      aria-label={title}
      height={height}
      width={height * aspect}
      className={className}
      style={style}
    >
      <title>{title}</title>
      <g>
        <path
          fill={wordmark}
          d="M6.02,46.77v-16.86H0v-2.74h15.06v2.74h-6.02v16.86h-3.02Z"
        />
        <path
          fill={wordmark}
          d="M19.07,46.77v-19.6h12.35v2.74h-9.32v5.63h8.54v2.74h-8.54v5.74h9.46v2.74h-12.49Z"
        />
        <path
          fill={wordmark}
          d="M36.54,46.77v-19.6h5.68l4.28,17.58h.45l4.28-17.58h5.68v19.6h-2.94v-17.47h-.45l-4.26,17.47h-5.1l-4.26-17.47h-.45v17.47h-2.94Z"
        />
        <path
          fill={wordmark}
          d="M61.54,46.77l5.6-19.6h5.32l5.57,19.6h-3.11l-1.29-4.62h-7.67l-1.29,4.62h-3.14ZM66.72,39.35h6.16l-2.86-10.3h-.45l-2.86,10.3Z"
        />
        <rect fill={mark} x="89.29" y="8.5" width="4.25" height="55.28" />
        <rect fill={mark} x="97.82" y="8.5" width="4.25" height="38.27" />
        <rect
          fill={mark}
          x="97.82"
          y="-17.01"
          width="4.25"
          height="38.27"
          transform="translate(97.82 102.08) rotate(-90)"
        />
      </g>
    </svg>
  );
}
