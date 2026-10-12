'use client';

import { useRef, useState, useEffect, KeyboardEvent, ClipboardEvent } from 'react';
import { cn } from '@/lib/utils';

interface TotpInputProps {
    length?: number;
    value: string;
    onChange: (value: string) => void;
    onComplete?: (value: string) => void;
    disabled?: boolean;
    autoFocus?: boolean;
    className?: string;
    error?: boolean;
}

export function TotpInput({
    length = 6,
    value,
    onChange,
    onComplete,
    disabled = false,
    autoFocus = true,
    className,
    error = false,
}: TotpInputProps) {
    const inputRefs = useRef<(HTMLInputElement | null)[]>([]);
    const [focusedIndex, setFocusedIndex] = useState<number | null>(null);
    const hasCalledComplete = useRef(false);

    // Initialize refs array
    useEffect(() => {
        inputRefs.current = inputRefs.current.slice(0, length);
    }, [length]);

    // Auto focus first input
    useEffect(() => {
        if (autoFocus && inputRefs.current[0]) {
            inputRefs.current[0].focus();
        }
    }, [autoFocus]);

    // Reset hasCalledComplete when value becomes incomplete
    useEffect(() => {
        if (value.length < length) {
            hasCalledComplete.current = false;
        }
    }, [value, length]);

    // Handle complete callback - only call once per complete input
    useEffect(() => {
        if (value.length === length && onComplete && !hasCalledComplete.current) {
            hasCalledComplete.current = true;
            onComplete(value);
        }
    }, [value, length, onComplete]);

    const handleChange = (index: number, inputValue: string) => {
        // Only accept digits
        const digit = inputValue.replace(/\D/g, '').slice(-1);

        if (digit) {
            const newValue = value.split('');
            newValue[index] = digit;
            const result = newValue.join('').slice(0, length);
            onChange(result);

            // Move to next input
            if (index < length - 1) {
                inputRefs.current[index + 1]?.focus();
            }
        }
    };

    const handleKeyDown = (index: number, e: KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Backspace') {
            e.preventDefault();
            const newValue = value.split('');

            if (newValue[index]) {
                // Clear current
                newValue[index] = '';
                onChange(newValue.join(''));
            } else if (index > 0) {
                // Move to previous and clear
                newValue[index - 1] = '';
                onChange(newValue.join(''));
                inputRefs.current[index - 1]?.focus();
            }
        } else if (e.key === 'ArrowLeft' && index > 0) {
            e.preventDefault();
            inputRefs.current[index - 1]?.focus();
        } else if (e.key === 'ArrowRight' && index < length - 1) {
            e.preventDefault();
            inputRefs.current[index + 1]?.focus();
        }
    };

    const handlePaste = (e: ClipboardEvent<HTMLInputElement>) => {
        e.preventDefault();
        const pastedData = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, length);
        if (pastedData) {
            onChange(pastedData);
            // Focus the next empty input or the last one
            const nextIndex = Math.min(pastedData.length, length - 1);
            inputRefs.current[nextIndex]?.focus();
        }
    };

    const handleFocus = (index: number) => {
        setFocusedIndex(index);
        // Select the content when focused
        inputRefs.current[index]?.select();
    };

    const handleBlur = () => {
        setFocusedIndex(null);
    };

    return (
        <div className={cn('flex gap-2 justify-center', className)}>
            {Array.from({ length }, (_, index) => (
                <input
                    key={index}
                    ref={(el) => {
                        inputRefs.current[index] = el;
                    }}
                    type="text"
                    inputMode="numeric"
                    maxLength={1}
                    value={value[index] || ''}
                    onChange={(e) => handleChange(index, e.target.value)}
                    onKeyDown={(e) => handleKeyDown(index, e)}
                    onPaste={handlePaste}
                    onFocus={() => handleFocus(index)}
                    onBlur={handleBlur}
                    disabled={disabled}
                    className={cn(
                        'w-12 h-14 text-center text-2xl font-bold rounded-lg',
                        'bg-[#09090b] border-2 text-white',
                        'focus:outline-none transition-all duration-200',
                        'disabled:opacity-50 disabled:cursor-not-allowed',
                        error
                            ? 'border-red-500 focus:border-red-500 animate-shake'
                            : focusedIndex === index
                                ? 'border-emerald-500 ring-2 ring-emerald-500/20'
                                : 'border-white/10 hover:border-white/20',
                        value[index] && !error && 'border-emerald-500/50'
                    )}
                    aria-label={`Digit ${index + 1}`}
                />
            ))}
        </div>
    );
}
