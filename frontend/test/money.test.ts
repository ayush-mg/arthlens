import { describe, expect, it } from 'vitest';
import {
  addMoney,
  applyDiscountAndTax,
  formatINR,
  fromMinorUnits,
  mulMoneyQty,
  subMoney,
  toMinorUnits,
} from '../lib/money';

describe('exact minor-unit money helpers', () => {
  it('rounds currency half-up at the conversion boundary', () => {
    expect(toMinorUnits('0.01')).toBe(BigInt(1));
    expect(toMinorUnits('0.005')).toBe(BigInt(1));
    expect(toMinorUnits('0.015')).toBe(BigInt(2));
    expect(toMinorUnits('-0.005')).toBe(BigInt(-1));
    expect(fromMinorUnits(BigInt('12345678901234567890'))).toBe('123456789012345678.90');
  });

  it('adds and subtracts without binary floating point', () => {
    expect(addMoney('0.10', '0.20')).toBe('0.30');
    expect(subMoney('0.10', '0.20')).toBe('-0.10');
  });

  it('multiplies prices by fractional quantities before rounding', () => {
    expect(mulMoneyQty('19.99', '0.125')).toBe('2.50');
    expect(mulMoneyQty('0.05', '0.1')).toBe('0.01');
  });

  it('allocates discounts then tax at the line boundary', () => {
    expect(applyDiscountAndTax('100.00', '10', '18')).toEqual({
      subtotal: '100.00',
      discount: '10.00',
      taxable: '90.00',
      tax: '16.20',
      total: '106.20',
    });
  });

  it('formats large values in Indian digit groups without converting to number', () => {
    expect(formatINR('123456789012345678.90')).toBe('₹1,23,45,67,89,01,23,45,678.90');
  });
});
