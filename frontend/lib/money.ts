/** Exact decimal money helpers. Monetary results are represented as fixed-point strings. */

type DecimalParts = { coefficient: bigint; scale: number };

function pow10(power: number): bigint {
  let value = BigInt(1);
  for (let index = 0; index < power; index += 1) value *= BigInt(10);
  return value;
}

function decimalParts(value: string | number): DecimalParts {
  const source = String(value).trim().replace(/,/g, "");
  const match = /^([+-]?)(\d+)(?:\.(\d*))?(?:e([+-]?\d+))?$/i.exec(source);
  if (!match) throw new TypeError(`Invalid decimal value: ${source}`);
  const sign = match[1] === "-" ? -BigInt(1) : BigInt(1);
  const whole = match[2];
  const fraction = match[3] ?? "";
  const exponent = Number(match[4] ?? "0");
  let scale = fraction.length - exponent;
  let coefficient = sign * BigInt(`${whole}${fraction}` || "0");
  if (scale < 0) {
    coefficient *= pow10(-scale);
    scale = 0;
  }
  return { coefficient, scale };
}

function roundHalfUp(numerator: bigint, denominator: bigint): bigint {
  if (denominator <= BigInt(0)) throw new RangeError("Denominator must be positive");
  const negative = numerator < BigInt(0);
  const absolute = negative ? -numerator : numerator;
  let quotient = absolute / denominator;
  const remainder = absolute % denominator;
  if (remainder * BigInt(2) >= denominator) quotient += BigInt(1);
  return negative ? -quotient : quotient;
}

function decimalToMinorUnits(value: string | number): bigint {
  const { coefficient, scale } = decimalParts(value);
  if (scale <= 2) return coefficient * pow10(2 - scale);
  return roundHalfUp(coefficient, pow10(scale - 2));
}

export function toMinorUnits(amount: string | number): bigint {
  return decimalToMinorUnits(amount);
}

export function fromMinorUnits(minor: bigint): string {
  const negative = minor < BigInt(0);
  const absolute = negative ? -minor : minor;
  const whole = absolute / BigInt(100);
  const fraction = String(absolute % BigInt(100)).padStart(2, "0");
  return `${negative ? "-" : ""}${whole}.${fraction}`;
}

export function addMoney(left: string | number, right: string | number): string {
  return fromMinorUnits(toMinorUnits(left) + toMinorUnits(right));
}

export function subMoney(left: string | number, right: string | number): string {
  return fromMinorUnits(toMinorUnits(left) - toMinorUnits(right));
}

export function mulMoneyQty(unitPrice: string | number, quantity: string | number): string {
  const price = decimalParts(unitPrice);
  const qty = decimalParts(quantity);
  const product = price.coefficient * qty.coefficient;
  const scale = price.scale + qty.scale;
  const minor = scale <= 2
    ? product * pow10(2 - scale)
    : roundHalfUp(product, pow10(scale - 2));
  return fromMinorUnits(minor);
}

function multiplyMinorByPercent(minor: bigint, percent: string | number): bigint {
  const rate = decimalParts(percent);
  const denominator = BigInt(100) * pow10(rate.scale);
  return roundHalfUp(minor * rate.coefficient, denominator);
}

export function applyDiscountAndTax(
  amount: string | number,
  discountPercent: string | number = "0",
  taxPercent: string | number = "0",
): { subtotal: string; discount: string; taxable: string; tax: string; total: string } {
  const subtotalMinor = toMinorUnits(amount);
  const discountMinor = multiplyMinorByPercent(subtotalMinor, discountPercent);
  const taxableMinor = subtotalMinor - discountMinor;
  const taxMinor = multiplyMinorByPercent(taxableMinor, taxPercent);
  return {
    subtotal: fromMinorUnits(subtotalMinor),
    discount: fromMinorUnits(discountMinor),
    taxable: fromMinorUnits(taxableMinor),
    tax: fromMinorUnits(taxMinor),
    total: fromMinorUnits(taxableMinor + taxMinor),
  };
}

export function formatINR(amount: string | number): string {
  const minor = toMinorUnits(amount);
  const negative = minor < BigInt(0);
  const absolute = negative ? -minor : minor;
  const rupees = absolute / BigInt(100);
  const paisa = String(absolute % BigInt(100)).padStart(2, "0");
  const groupedRupees = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(rupees);
  return `${negative ? "-" : ""}₹${groupedRupees}.${paisa}`;
}
