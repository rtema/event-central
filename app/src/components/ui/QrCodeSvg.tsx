import { useMemo } from "react";
import { qrToMatrix } from "../users/qrcode";

export interface QrCodeSvgProps {
  /** The string to encode (e.g. an otpauth:// URI). */
  value: string;
  /** Rendered width/height in pixels. */
  size?: number;
  /** Module colour. Defaults to a near-black navy for high scan contrast. */
  color?: string;
  /** Background colour. Must stay light for reliable scanning. */
  background?: string;
  /** Quiet-zone width in modules (the spec requires at least 4). */
  quietZone?: number;
  className?: string;
}

/**
 * Renders a QR code as a crisp, self-contained SVG. Encoding happens locally
 * via ./qrcode, so the value (which may contain a TOTP secret) never leaves the
 * browser. Dark modules are emitted as a single <path> for compactness.
 */
export function QrCodeSvg({
  value,
  size = 220,
  color = "#001026",
  background = "#ffffff",
  quietZone = 4,
  className,
}: QrCodeSvgProps) {
  const { path, dim } = useMemo(() => {
    const matrix = qrToMatrix(value);
    const n = matrix.length;
    const dim = n + quietZone * 2;
    let d = "";
    for (let y = 0; y < n; y++) {
      for (let x = 0; x < n; x++) {
        if (matrix[y][x]) {
          d += `M${x + quietZone},${y + quietZone}h1v1h-1z`;
        }
      }
    }
    return { path: d, dim };
  }, [value, quietZone]);

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${dim} ${dim}`}
      shapeRendering="crispEdges"
      role="img"
      aria-label="QR code"
      className={className}
    >
      <rect width={dim} height={dim} fill={background} />
      <path d={path} fill={color} />
    </svg>
  );
}
