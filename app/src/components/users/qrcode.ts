/*
 * Minimal QR Code generator (byte mode only).
 *
 * Ported and trimmed from the QR Code generator library by Project Nayuki
 * (MIT License, https://www.nayuki.io/page/qr-code-generator-library). Only the
 * byte-mode path is kept — enough to encode an `otpauth://` URI — and the source
 * has been rewritten to avoid TypeScript `namespace`, `enum`, and constructor
 * parameter-property syntax so it satisfies this project's `erasableSyntaxOnly`
 * compiler setting. Generation is fully local: no data leaves the browser, which
 * matters because the encoded payload contains a TOTP secret.
 *
 * Returns a square matrix of booleans (true = dark module) via `qrToMatrix()`.
 */

type bit = number;
type byte = number;
type int = number;

/** Error-correction level. `ordinal` indexes the tables; `formatBits` is the 2-bit field. */
export interface Ecc {
  ordinal: int;
  formatBits: int;
}

export const ECC: Record<"LOW" | "MEDIUM" | "QUARTILE" | "HIGH", Ecc> = {
  LOW: { ordinal: 0, formatBits: 1 },
  MEDIUM: { ordinal: 1, formatBits: 0 },
  QUARTILE: { ordinal: 2, formatBits: 3 },
  HIGH: { ordinal: 3, formatBits: 2 },
};

const MIN_VERSION = 1;
const MAX_VERSION = 40;
const PENALTY_N1 = 3;
const PENALTY_N2 = 3;
const PENALTY_N3 = 40;
const PENALTY_N4 = 10;

// ECC codewords per block, indexed [ecl.ordinal][version]. Index 0 is padding.
const ECC_CODEWORDS_PER_BLOCK: int[][] = [
  [
    -1, 7, 10, 15, 20, 26, 18, 20, 24, 30, 18, 20, 24, 26, 30, 22, 24, 28, 30,
    28, 28, 28, 28, 30, 30, 26, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30,
    30, 30, 30,
  ],
  [
    -1, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26, 30, 22, 22, 24, 24, 28, 28, 26,
    26, 26, 26, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28,
    28, 28, 28,
  ],
  [
    -1, 13, 22, 18, 26, 18, 24, 18, 22, 20, 24, 28, 26, 24, 20, 30, 24, 28, 28,
    26, 30, 28, 30, 30, 30, 30, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30,
    30, 30, 30,
  ],
  [
    -1, 17, 28, 22, 16, 22, 28, 26, 26, 24, 28, 24, 28, 22, 24, 24, 30, 28, 28,
    26, 28, 30, 24, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30,
    30, 30, 30,
  ],
];

// Number of ECC blocks, indexed [ecl.ordinal][version]. Index 0 is padding.
const NUM_ERROR_CORRECTION_BLOCKS: int[][] = [
  [
    -1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 4, 4, 4, 4, 4, 6, 6, 6, 6, 7, 8, 8, 9, 9, 10,
    12, 12, 12, 13, 14, 15, 16, 17, 18, 19, 19, 20, 21, 22, 24, 25,
  ],
  [
    -1, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5, 5, 8, 9, 9, 10, 10, 11, 13, 14, 16, 17,
    17, 18, 20, 21, 23, 25, 26, 28, 29, 31, 33, 35, 37, 38, 40, 43, 45, 47, 49,
  ],
  [
    -1, 1, 1, 2, 2, 4, 4, 6, 6, 8, 8, 8, 10, 12, 16, 12, 17, 16, 18, 21, 20, 23,
    23, 25, 27, 29, 34, 34, 35, 38, 40, 43, 45, 48, 51, 53, 56, 59, 62, 65, 68,
  ],
  [
    -1, 1, 1, 2, 4, 4, 4, 5, 6, 8, 8, 11, 11, 16, 16, 18, 16, 19, 21, 25, 25,
    25, 34, 30, 32, 35, 37, 40, 42, 45, 48, 51, 54, 57, 60, 63, 66, 70, 74, 77,
    81,
  ],
];

function assert(cond: boolean): void {
  if (!cond) throw new Error("Assertion error");
}

function getBit(x: int, i: int): boolean {
  return ((x >>> i) & 1) != 0;
}

function appendBits(val: int, len: int, bb: bit[]): void {
  if (len < 0 || len > 31 || val >>> len != 0)
    throw new RangeError("Value out of range");
  for (let i = len - 1; i >= 0; i--) bb.push((val >>> i) & 1);
}

function getNumRawDataModules(ver: int): int {
  if (ver < MIN_VERSION || ver > MAX_VERSION)
    throw new RangeError("Version number out of range");
  let result: int = (16 * ver + 128) * ver + 64;
  if (ver >= 2) {
    const numAlign: int = Math.floor(ver / 7) + 2;
    result -= (25 * numAlign - 10) * numAlign - 55;
    if (ver >= 7) result -= 36;
  }
  assert(208 <= result && result <= 29648);
  return result;
}

function getNumDataCodewords(ver: int, ecl: Ecc): int {
  return (
    Math.floor(getNumRawDataModules(ver) / 8) -
    ECC_CODEWORDS_PER_BLOCK[ecl.ordinal][ver] *
      NUM_ERROR_CORRECTION_BLOCKS[ecl.ordinal][ver]
  );
}

function reedSolomonMultiply(x: byte, y: byte): byte {
  if (x >>> 8 != 0 || y >>> 8 != 0) throw new RangeError("Byte out of range");
  let z: int = 0;
  for (let i = 7; i >= 0; i--) {
    z = (z << 1) ^ ((z >>> 7) * 0x11d);
    z ^= ((y >>> i) & 1) * x;
  }
  assert(z >>> 8 == 0);
  return z as byte;
}

function reedSolomonComputeDivisor(degree: int): byte[] {
  if (degree < 1 || degree > 255) throw new RangeError("Degree out of range");
  const result: byte[] = [];
  for (let i = 0; i < degree - 1; i++) result.push(0);
  result.push(1);
  let root = 1;
  for (let i = 0; i < degree; i++) {
    for (let j = 0; j < result.length; j++) {
      result[j] = reedSolomonMultiply(result[j], root);
      if (j + 1 < result.length) result[j] ^= result[j + 1];
    }
    root = reedSolomonMultiply(root, 0x02);
  }
  return result;
}

function reedSolomonComputeRemainder(
  data: readonly byte[],
  divisor: readonly byte[],
): byte[] {
  const result: byte[] = divisor.map(() => 0);
  for (const b of data) {
    const factor: byte = b ^ (result.shift() as byte);
    result.push(0);
    divisor.forEach(
      (coef, i) => (result[i] ^= reedSolomonMultiply(coef, factor)),
    );
  }
  return result;
}

/** Byte-mode char-count bits for the version's size group. */
function byteModeCharCountBits(ver: int): int {
  return [8, 16, 16][Math.floor((ver + 7) / 17)];
}

class QrCode {
  readonly size: int;
  readonly version: int;
  readonly errorCorrectionLevel: Ecc;
  mask: int;
  private readonly modules: boolean[][] = [];
  private readonly isFunction: boolean[][] = [];

  constructor(
    version: int,
    errorCorrectionLevel: Ecc,
    dataCodewords: readonly byte[],
    msk: int,
  ) {
    this.version = version;
    this.errorCorrectionLevel = errorCorrectionLevel;
    if (version < MIN_VERSION || version > MAX_VERSION)
      throw new RangeError("Version value out of range");
    if (msk < -1 || msk > 7) throw new RangeError("Mask value out of range");
    this.size = version * 4 + 17;

    const row: boolean[] = [];
    for (let i = 0; i < this.size; i++) row.push(false);
    for (let i = 0; i < this.size; i++) {
      this.modules.push(row.slice());
      this.isFunction.push(row.slice());
    }

    this.drawFunctionPatterns();
    const allCodewords: byte[] = this.addEccAndInterleave(dataCodewords);
    this.drawCodewords(allCodewords);

    if (msk == -1) {
      let minPenalty: int = 1000000000;
      for (let i = 0; i < 8; i++) {
        this.applyMask(i);
        this.drawFormatBits(i);
        const penalty: int = this.getPenaltyScore();
        if (penalty < minPenalty) {
          msk = i;
          minPenalty = penalty;
        }
        this.applyMask(i);
      }
    }
    assert(0 <= msk && msk <= 7);
    this.mask = msk;
    this.applyMask(msk);
    this.drawFormatBits(msk);
  }

  getModule(x: int, y: int): boolean {
    return (
      0 <= x && x < this.size && 0 <= y && y < this.size && this.modules[y][x]
    );
  }

  private drawFunctionPatterns(): void {
    for (let i = 0; i < this.size; i++) {
      this.setFunctionModule(6, i, i % 2 == 0);
      this.setFunctionModule(i, 6, i % 2 == 0);
    }
    this.drawFinderPattern(3, 3);
    this.drawFinderPattern(this.size - 4, 3);
    this.drawFinderPattern(3, this.size - 4);

    const alignPatPos: int[] = this.getAlignmentPatternPositions();
    const numAlign: int = alignPatPos.length;
    for (let i = 0; i < numAlign; i++) {
      for (let j = 0; j < numAlign; j++) {
        if (
          !(
            (i == 0 && j == 0) ||
            (i == 0 && j == numAlign - 1) ||
            (i == numAlign - 1 && j == 0)
          )
        )
          this.drawAlignmentPattern(alignPatPos[i], alignPatPos[j]);
      }
    }
    this.drawFormatBits(0);
    this.drawVersion();
  }

  private drawFormatBits(mask: int): void {
    const data: int = (this.errorCorrectionLevel.formatBits << 3) | mask;
    let rem: int = data;
    for (let i = 0; i < 10; i++) rem = (rem << 1) ^ ((rem >>> 9) * 0x537);
    const bits = ((data << 10) | rem) ^ 0x5412;
    assert(bits >>> 15 == 0);

    for (let i = 0; i <= 5; i++) this.setFunctionModule(8, i, getBit(bits, i));
    this.setFunctionModule(8, 7, getBit(bits, 6));
    this.setFunctionModule(8, 8, getBit(bits, 7));
    this.setFunctionModule(7, 8, getBit(bits, 8));
    for (let i = 9; i < 15; i++)
      this.setFunctionModule(14 - i, 8, getBit(bits, i));

    for (let i = 0; i < 8; i++)
      this.setFunctionModule(this.size - 1 - i, 8, getBit(bits, i));
    for (let i = 8; i < 15; i++)
      this.setFunctionModule(8, this.size - 15 + i, getBit(bits, i));
    this.setFunctionModule(8, this.size - 8, true);
  }

  private drawVersion(): void {
    if (this.version < 7) return;
    let rem: int = this.version;
    for (let i = 0; i < 12; i++) rem = (rem << 1) ^ ((rem >>> 11) * 0x1f25);
    const bits: int = (this.version << 12) | rem;
    assert(bits >>> 18 == 0);
    for (let i = 0; i < 18; i++) {
      const color: boolean = getBit(bits, i);
      const a: int = this.size - 11 + (i % 3);
      const b: int = Math.floor(i / 3);
      this.setFunctionModule(a, b, color);
      this.setFunctionModule(b, a, color);
    }
  }

  private drawFinderPattern(x: int, y: int): void {
    for (let dy = -4; dy <= 4; dy++) {
      for (let dx = -4; dx <= 4; dx++) {
        const dist: int = Math.max(Math.abs(dx), Math.abs(dy));
        const xx: int = x + dx;
        const yy: int = y + dy;
        if (0 <= xx && xx < this.size && 0 <= yy && yy < this.size)
          this.setFunctionModule(xx, yy, dist != 2 && dist != 4);
      }
    }
  }

  private drawAlignmentPattern(x: int, y: int): void {
    for (let dy = -2; dy <= 2; dy++) {
      for (let dx = -2; dx <= 2; dx++)
        this.setFunctionModule(
          x + dx,
          y + dy,
          Math.max(Math.abs(dx), Math.abs(dy)) != 1,
        );
    }
  }

  private setFunctionModule(x: int, y: int, isDark: boolean): void {
    this.modules[y][x] = isDark;
    this.isFunction[y][x] = true;
  }

  private addEccAndInterleave(data: readonly byte[]): byte[] {
    const ver: int = this.version;
    const ecl: Ecc = this.errorCorrectionLevel;
    if (data.length != getNumDataCodewords(ver, ecl))
      throw new RangeError("Invalid argument");

    const numBlocks: int = NUM_ERROR_CORRECTION_BLOCKS[ecl.ordinal][ver];
    const blockEccLen: int = ECC_CODEWORDS_PER_BLOCK[ecl.ordinal][ver];
    const rawCodewords: int = Math.floor(getNumRawDataModules(ver) / 8);
    const numShortBlocks: int = numBlocks - (rawCodewords % numBlocks);
    const shortBlockLen: int = Math.floor(rawCodewords / numBlocks);

    const blocks: byte[][] = [];
    const rsDiv: byte[] = reedSolomonComputeDivisor(blockEccLen);
    for (let i = 0, k = 0; i < numBlocks; i++) {
      const dat: byte[] = data.slice(
        k,
        k + shortBlockLen - blockEccLen + (i < numShortBlocks ? 0 : 1),
      );
      k += dat.length;
      const ecc: byte[] = reedSolomonComputeRemainder(dat, rsDiv);
      if (i < numShortBlocks) dat.push(0);
      blocks.push(dat.concat(ecc));
    }

    const result: byte[] = [];
    for (let i = 0; i < blocks[0].length; i++) {
      blocks.forEach((block, j) => {
        if (i != shortBlockLen - blockEccLen || j >= numShortBlocks)
          result.push(block[i]);
      });
    }
    assert(result.length == rawCodewords);
    return result;
  }

  private drawCodewords(data: readonly byte[]): void {
    if (data.length != Math.floor(getNumRawDataModules(this.version) / 8))
      throw new RangeError("Invalid argument");
    let i: int = 0;
    for (let right = this.size - 1; right >= 1; right -= 2) {
      if (right == 6) right = 5;
      for (let vert = 0; vert < this.size; vert++) {
        for (let j = 0; j < 2; j++) {
          const x: int = right - j;
          const upward: boolean = ((right + 1) & 2) == 0;
          const y: int = upward ? this.size - 1 - vert : vert;
          if (!this.isFunction[y][x] && i < data.length * 8) {
            this.modules[y][x] = getBit(data[i >>> 3], 7 - (i & 7));
            i++;
          }
        }
      }
    }
    assert(i == data.length * 8);
  }

  private applyMask(mask: int): void {
    if (mask < 0 || mask > 7) throw new RangeError("Mask value out of range");
    for (let y = 0; y < this.size; y++) {
      for (let x = 0; x < this.size; x++) {
        let invert: boolean;
        switch (mask) {
          case 0:
            invert = (x + y) % 2 == 0;
            break;
          case 1:
            invert = y % 2 == 0;
            break;
          case 2:
            invert = x % 3 == 0;
            break;
          case 3:
            invert = (x + y) % 3 == 0;
            break;
          case 4:
            invert = (Math.floor(x / 3) + Math.floor(y / 2)) % 2 == 0;
            break;
          case 5:
            invert = ((x * y) % 2) + ((x * y) % 3) == 0;
            break;
          case 6:
            invert = (((x * y) % 2) + ((x * y) % 3)) % 2 == 0;
            break;
          case 7:
            invert = (((x + y) % 2) + ((x * y) % 3)) % 2 == 0;
            break;
          default:
            throw new Error("Unreachable");
        }
        if (!this.isFunction[y][x] && invert)
          this.modules[y][x] = !this.modules[y][x];
      }
    }
  }

  private getPenaltyScore(): int {
    let result: int = 0;
    for (let y = 0; y < this.size; y++) {
      let runColor = false;
      let runX = 0;
      const runHistory = [0, 0, 0, 0, 0, 0, 0];
      for (let x = 0; x < this.size; x++) {
        if (this.modules[y][x] == runColor) {
          runX++;
          if (runX == 5) result += PENALTY_N1;
          else if (runX > 5) result++;
        } else {
          this.finderPenaltyAddHistory(runX, runHistory);
          if (!runColor)
            result += this.finderPenaltyCountPatterns(runHistory) * PENALTY_N3;
          runColor = this.modules[y][x];
          runX = 1;
        }
      }
      result +=
        this.finderPenaltyTerminateAndCount(runColor, runX, runHistory) *
        PENALTY_N3;
    }
    for (let x = 0; x < this.size; x++) {
      let runColor = false;
      let runY = 0;
      const runHistory = [0, 0, 0, 0, 0, 0, 0];
      for (let y = 0; y < this.size; y++) {
        if (this.modules[y][x] == runColor) {
          runY++;
          if (runY == 5) result += PENALTY_N1;
          else if (runY > 5) result++;
        } else {
          this.finderPenaltyAddHistory(runY, runHistory);
          if (!runColor)
            result += this.finderPenaltyCountPatterns(runHistory) * PENALTY_N3;
          runColor = this.modules[y][x];
          runY = 1;
        }
      }
      result +=
        this.finderPenaltyTerminateAndCount(runColor, runY, runHistory) *
        PENALTY_N3;
    }

    for (let y = 0; y < this.size - 1; y++) {
      for (let x = 0; x < this.size - 1; x++) {
        const color: boolean = this.modules[y][x];
        if (
          color == this.modules[y][x + 1] &&
          color == this.modules[y + 1][x] &&
          color == this.modules[y + 1][x + 1]
        )
          result += PENALTY_N2;
      }
    }

    let dark: int = 0;
    for (const row of this.modules)
      dark = row.reduce((sum, color) => sum + (color ? 1 : 0), dark);
    const total: int = this.size * this.size;
    const k: int = Math.ceil(Math.abs(dark * 20 - total * 10) / total) - 1;
    assert(0 <= k && k <= 9);
    result += k * PENALTY_N4;
    return result;
  }

  private getAlignmentPatternPositions(): int[] {
    if (this.version == 1) return [];
    const numAlign: int = Math.floor(this.version / 7) + 2;
    const step: int =
      Math.floor((this.version * 8 + numAlign * 3 + 5) / (numAlign * 4 - 4)) *
      2;
    const result: int[] = [6];
    for (let pos = this.size - 7; result.length < numAlign; pos -= step)
      result.splice(1, 0, pos);
    return result;
  }

  private finderPenaltyCountPatterns(runHistory: readonly int[]): int {
    const n: int = runHistory[1];
    assert(n <= this.size * 3);
    const core: boolean =
      n > 0 &&
      runHistory[2] == n &&
      runHistory[3] == n * 3 &&
      runHistory[4] == n &&
      runHistory[5] == n;
    return (
      (core && runHistory[0] >= n * 4 && runHistory[6] >= n ? 1 : 0) +
      (core && runHistory[6] >= n * 4 && runHistory[0] >= n ? 1 : 0)
    );
  }

  private finderPenaltyTerminateAndCount(
    currentRunColor: boolean,
    currentRunLength: int,
    runHistory: int[],
  ): int {
    if (currentRunColor) {
      this.finderPenaltyAddHistory(currentRunLength, runHistory);
      currentRunLength = 0;
    }
    currentRunLength += this.size;
    this.finderPenaltyAddHistory(currentRunLength, runHistory);
    return this.finderPenaltyCountPatterns(runHistory);
  }

  private finderPenaltyAddHistory(
    currentRunLength: int,
    runHistory: int[],
  ): void {
    if (runHistory[0] == 0) currentRunLength += this.size;
    runHistory.pop();
    runHistory.unshift(currentRunLength);
  }
}

/** Encodes the given bytes in byte mode and returns a finished QR Code. */
function encodeBytes(data: readonly byte[], ecl: Ecc): QrCode {
  // Pick the smallest version that fits the data at the requested ECC level.
  let version = MIN_VERSION;
  let dataUsedBits = 0;
  for (; ; version++) {
    const dataCapacityBits = getNumDataCodewords(version, ecl) * 8;
    const usedBits = 4 + byteModeCharCountBits(version) + data.length * 8;
    if (usedBits <= dataCapacityBits) {
      dataUsedBits = usedBits;
      break;
    }
    if (version >= MAX_VERSION) throw new RangeError("Data too long");
  }

  // Boost ECC level for free if the data still fits.
  for (const newEcl of [ECC.MEDIUM, ECC.QUARTILE, ECC.HIGH]) {
    if (dataUsedBits <= getNumDataCodewords(version, newEcl) * 8) ecl = newEcl;
  }

  // Build the bit buffer: mode indicator, char count, payload.
  const bb: bit[] = [];
  appendBits(0x4, 4, bb); // byte mode
  appendBits(data.length, byteModeCharCountBits(version), bb);
  for (const b of data) appendBits(b, 8, bb);

  // Terminator + byte alignment + alternating pad bytes.
  const dataCapacityBits = getNumDataCodewords(version, ecl) * 8;
  appendBits(0, Math.min(4, dataCapacityBits - bb.length), bb);
  appendBits(0, (8 - (bb.length % 8)) % 8, bb);
  for (let padByte = 0xec; bb.length < dataCapacityBits; padByte ^= 0xec ^ 0x11)
    appendBits(padByte, 8, bb);

  const dataCodewords: byte[] = [];
  while (dataCodewords.length * 8 < bb.length) dataCodewords.push(0);
  bb.forEach((b, i) => (dataCodewords[i >>> 3] |= b << (7 - (i & 7))));

  return new QrCode(version, ecl, dataCodewords, -1);
}

function toUtf8Bytes(str: string): byte[] {
  const out: byte[] = [];
  const encoded = encodeURIComponent(str);
  for (let i = 0; i < encoded.length; i++) {
    if (encoded[i] === "%") {
      out.push(parseInt(encoded.substring(i + 1, i + 3), 16));
      i += 2;
    } else {
      out.push(encoded.charCodeAt(i));
    }
  }
  return out;
}

/**
 * Encodes `text` (UTF-8, byte mode) into a QR Code and returns it as a square
 * matrix of booleans where `true` means a dark module. Error correction
 * defaults to "M", auto-boosted when spare capacity allows.
 */
export function qrToMatrix(text: string, ecl: Ecc = ECC.MEDIUM): boolean[][] {
  const qr = encodeBytes(toUtf8Bytes(text), ecl);
  const matrix: boolean[][] = [];
  for (let y = 0; y < qr.size; y++) {
    const line: boolean[] = [];
    for (let x = 0; x < qr.size; x++) line.push(qr.getModule(x, y));
    matrix.push(line);
  }
  return matrix;
}
