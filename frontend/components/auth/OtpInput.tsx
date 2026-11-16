'use client';

import { ClipboardEvent, KeyboardEvent, useRef } from 'react';

export function OtpInput({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const inputs = useRef<Array<HTMLInputElement | null>>([]);
  const digits = Array.from({ length: 6 }, (_, index) => value[index] ?? '');

  const applyPaste = (event: ClipboardEvent<HTMLInputElement>) => {
    const pasted = event.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (!pasted) return;
    event.preventDefault();
    onChange(pasted);
    inputs.current[Math.min(pasted.length, 5)]?.focus();
  };

  const handleKey = (event: KeyboardEvent<HTMLInputElement>, index: number) => {
    if (event.key === 'Backspace' && !digits[index] && index > 0) inputs.current[index - 1]?.focus();
    if (event.key === 'ArrowLeft' && index > 0) inputs.current[index - 1]?.focus();
    if (event.key === 'ArrowRight' && index < 5) inputs.current[index + 1]?.focus();
  };

  return (
    <div className="flex justify-between gap-2" role="group" aria-label="Six digit email verification code">
      {digits.map((digit, index) => (
        <input
          key={index}
          ref={(node) => { inputs.current[index] = node; }}
          aria-label={`Code digit ${index + 1}`}
          autoComplete={index === 0 ? 'one-time-code' : 'off'}
          inputMode="numeric"
          pattern="[0-9]*"
          maxLength={6}
          value={digit}
          onPaste={applyPaste}
          onKeyDown={(event) => handleKey(event, index)}
          onChange={(event) => {
            const next = event.target.value.replace(/\D/g, '');
            if (next.length > 1) {
              const pasted = next.slice(0, 6);
              onChange(pasted);
              inputs.current[Math.min(pasted.length, 5)]?.focus();
              return;
            }
            const nextDigits = [...digits];
            nextDigits[index] = next.slice(-1);
            onChange(nextDigits.join('').slice(0, 6));
            if (next && index < 5) inputs.current[index + 1]?.focus();
          }}
          className="h-14 min-w-0 flex-1 rounded-2xl border border-white/10 bg-white/[0.045] text-center font-mono text-xl font-semibold tabular-nums text-white outline-none transition focus:border-emerald-300/70 focus:bg-emerald-300/[0.08] focus:ring-2 focus:ring-emerald-300/20"
        />
      ))}
    </div>
  );
}
