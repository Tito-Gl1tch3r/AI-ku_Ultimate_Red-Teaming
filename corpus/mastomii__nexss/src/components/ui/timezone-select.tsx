'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { ChevronDown, Search, Check } from 'lucide-react';
import { cn } from '@/lib/utils';

// Complete list of IANA timezones
const ALL_TIMEZONES = [
    // UTC
    { value: 'UTC', label: 'UTC', offset: '+00:00' },
    
    // Africa
    { value: 'Africa/Abidjan', label: 'Africa/Abidjan', offset: '+00:00' },
    { value: 'Africa/Accra', label: 'Africa/Accra', offset: '+00:00' },
    { value: 'Africa/Addis_Ababa', label: 'Africa/Addis Ababa', offset: '+03:00' },
    { value: 'Africa/Algiers', label: 'Africa/Algiers', offset: '+01:00' },
    { value: 'Africa/Cairo', label: 'Africa/Cairo', offset: '+02:00' },
    { value: 'Africa/Casablanca', label: 'Africa/Casablanca', offset: '+01:00' },
    { value: 'Africa/Johannesburg', label: 'Africa/Johannesburg', offset: '+02:00' },
    { value: 'Africa/Lagos', label: 'Africa/Lagos', offset: '+01:00' },
    { value: 'Africa/Nairobi', label: 'Africa/Nairobi', offset: '+03:00' },
    { value: 'Africa/Tunis', label: 'Africa/Tunis', offset: '+01:00' },
    
    // America
    { value: 'America/Anchorage', label: 'America/Anchorage', offset: '-09:00' },
    { value: 'America/Argentina/Buenos_Aires', label: 'America/Buenos Aires', offset: '-03:00' },
    { value: 'America/Bogota', label: 'America/Bogota', offset: '-05:00' },
    { value: 'America/Caracas', label: 'America/Caracas', offset: '-04:00' },
    { value: 'America/Chicago', label: 'America/Chicago (CST)', offset: '-06:00' },
    { value: 'America/Denver', label: 'America/Denver (MST)', offset: '-07:00' },
    { value: 'America/Halifax', label: 'America/Halifax', offset: '-04:00' },
    { value: 'America/Havana', label: 'America/Havana', offset: '-05:00' },
    { value: 'America/Lima', label: 'America/Lima', offset: '-05:00' },
    { value: 'America/Los_Angeles', label: 'America/Los Angeles (PST)', offset: '-08:00' },
    { value: 'America/Mexico_City', label: 'America/Mexico City', offset: '-06:00' },
    { value: 'America/New_York', label: 'America/New York (EST)', offset: '-05:00' },
    { value: 'America/Panama', label: 'America/Panama', offset: '-05:00' },
    { value: 'America/Phoenix', label: 'America/Phoenix', offset: '-07:00' },
    { value: 'America/Santiago', label: 'America/Santiago', offset: '-03:00' },
    { value: 'America/Sao_Paulo', label: 'America/Sao Paulo', offset: '-03:00' },
    { value: 'America/Toronto', label: 'America/Toronto', offset: '-05:00' },
    { value: 'America/Vancouver', label: 'America/Vancouver', offset: '-08:00' },
    
    // Asia
    { value: 'Asia/Almaty', label: 'Asia/Almaty', offset: '+06:00' },
    { value: 'Asia/Amman', label: 'Asia/Amman', offset: '+03:00' },
    { value: 'Asia/Baghdad', label: 'Asia/Baghdad', offset: '+03:00' },
    { value: 'Asia/Baku', label: 'Asia/Baku', offset: '+04:00' },
    { value: 'Asia/Bangkok', label: 'Asia/Bangkok', offset: '+07:00' },
    { value: 'Asia/Beirut', label: 'Asia/Beirut', offset: '+02:00' },
    { value: 'Asia/Colombo', label: 'Asia/Colombo', offset: '+05:30' },
    { value: 'Asia/Dhaka', label: 'Asia/Dhaka', offset: '+06:00' },
    { value: 'Asia/Dubai', label: 'Asia/Dubai', offset: '+04:00' },
    { value: 'Asia/Ho_Chi_Minh', label: 'Asia/Ho Chi Minh', offset: '+07:00' },
    { value: 'Asia/Hong_Kong', label: 'Asia/Hong Kong', offset: '+08:00' },
    { value: 'Asia/Istanbul', label: 'Asia/Istanbul', offset: '+03:00' },
    { value: 'Asia/Jakarta', label: 'Asia/Jakarta (WIB)', offset: '+07:00' },
    { value: 'Asia/Jayapura', label: 'Asia/Jayapura (WIT)', offset: '+09:00' },
    { value: 'Asia/Jerusalem', label: 'Asia/Jerusalem', offset: '+02:00' },
    { value: 'Asia/Kabul', label: 'Asia/Kabul', offset: '+04:30' },
    { value: 'Asia/Karachi', label: 'Asia/Karachi', offset: '+05:00' },
    { value: 'Asia/Kathmandu', label: 'Asia/Kathmandu', offset: '+05:45' },
    { value: 'Asia/Kolkata', label: 'Asia/Kolkata', offset: '+05:30' },
    { value: 'Asia/Kuala_Lumpur', label: 'Asia/Kuala Lumpur', offset: '+08:00' },
    { value: 'Asia/Kuwait', label: 'Asia/Kuwait', offset: '+03:00' },
    { value: 'Asia/Makassar', label: 'Asia/Makassar (WITA)', offset: '+08:00' },
    { value: 'Asia/Manila', label: 'Asia/Manila', offset: '+08:00' },
    { value: 'Asia/Muscat', label: 'Asia/Muscat', offset: '+04:00' },
    { value: 'Asia/Riyadh', label: 'Asia/Riyadh', offset: '+03:00' },
    { value: 'Asia/Seoul', label: 'Asia/Seoul (KST)', offset: '+09:00' },
    { value: 'Asia/Shanghai', label: 'Asia/Shanghai (CST)', offset: '+08:00' },
    { value: 'Asia/Singapore', label: 'Asia/Singapore (SGT)', offset: '+08:00' },
    { value: 'Asia/Taipei', label: 'Asia/Taipei', offset: '+08:00' },
    { value: 'Asia/Tehran', label: 'Asia/Tehran', offset: '+03:30' },
    { value: 'Asia/Tokyo', label: 'Asia/Tokyo (JST)', offset: '+09:00' },
    { value: 'Asia/Vladivostok', label: 'Asia/Vladivostok', offset: '+10:00' },
    { value: 'Asia/Yangon', label: 'Asia/Yangon', offset: '+06:30' },
    
    // Atlantic
    { value: 'Atlantic/Azores', label: 'Atlantic/Azores', offset: '-01:00' },
    { value: 'Atlantic/Reykjavik', label: 'Atlantic/Reykjavik', offset: '+00:00' },
    
    // Australia
    { value: 'Australia/Adelaide', label: 'Australia/Adelaide', offset: '+09:30' },
    { value: 'Australia/Brisbane', label: 'Australia/Brisbane', offset: '+10:00' },
    { value: 'Australia/Darwin', label: 'Australia/Darwin', offset: '+09:30' },
    { value: 'Australia/Hobart', label: 'Australia/Hobart', offset: '+10:00' },
    { value: 'Australia/Melbourne', label: 'Australia/Melbourne', offset: '+10:00' },
    { value: 'Australia/Perth', label: 'Australia/Perth', offset: '+08:00' },
    { value: 'Australia/Sydney', label: 'Australia/Sydney (AEST)', offset: '+10:00' },
    
    // Europe
    { value: 'Europe/Amsterdam', label: 'Europe/Amsterdam', offset: '+01:00' },
    { value: 'Europe/Athens', label: 'Europe/Athens', offset: '+02:00' },
    { value: 'Europe/Belgrade', label: 'Europe/Belgrade', offset: '+01:00' },
    { value: 'Europe/Berlin', label: 'Europe/Berlin (CET)', offset: '+01:00' },
    { value: 'Europe/Brussels', label: 'Europe/Brussels', offset: '+01:00' },
    { value: 'Europe/Bucharest', label: 'Europe/Bucharest', offset: '+02:00' },
    { value: 'Europe/Budapest', label: 'Europe/Budapest', offset: '+01:00' },
    { value: 'Europe/Copenhagen', label: 'Europe/Copenhagen', offset: '+01:00' },
    { value: 'Europe/Dublin', label: 'Europe/Dublin', offset: '+00:00' },
    { value: 'Europe/Helsinki', label: 'Europe/Helsinki', offset: '+02:00' },
    { value: 'Europe/Kiev', label: 'Europe/Kiev', offset: '+02:00' },
    { value: 'Europe/Lisbon', label: 'Europe/Lisbon', offset: '+00:00' },
    { value: 'Europe/London', label: 'Europe/London (GMT)', offset: '+00:00' },
    { value: 'Europe/Madrid', label: 'Europe/Madrid', offset: '+01:00' },
    { value: 'Europe/Moscow', label: 'Europe/Moscow (MSK)', offset: '+03:00' },
    { value: 'Europe/Oslo', label: 'Europe/Oslo', offset: '+01:00' },
    { value: 'Europe/Paris', label: 'Europe/Paris (CET)', offset: '+01:00' },
    { value: 'Europe/Prague', label: 'Europe/Prague', offset: '+01:00' },
    { value: 'Europe/Rome', label: 'Europe/Rome', offset: '+01:00' },
    { value: 'Europe/Stockholm', label: 'Europe/Stockholm', offset: '+01:00' },
    { value: 'Europe/Vienna', label: 'Europe/Vienna', offset: '+01:00' },
    { value: 'Europe/Warsaw', label: 'Europe/Warsaw', offset: '+01:00' },
    { value: 'Europe/Zurich', label: 'Europe/Zurich', offset: '+01:00' },
    
    // Indian
    { value: 'Indian/Maldives', label: 'Indian/Maldives', offset: '+05:00' },
    { value: 'Indian/Mauritius', label: 'Indian/Mauritius', offset: '+04:00' },
    
    // Pacific
    { value: 'Pacific/Auckland', label: 'Pacific/Auckland (NZST)', offset: '+12:00' },
    { value: 'Pacific/Fiji', label: 'Pacific/Fiji', offset: '+12:00' },
    { value: 'Pacific/Guam', label: 'Pacific/Guam', offset: '+10:00' },
    { value: 'Pacific/Honolulu', label: 'Pacific/Honolulu', offset: '-10:00' },
    { value: 'Pacific/Midway', label: 'Pacific/Midway', offset: '-11:00' },
    { value: 'Pacific/Noumea', label: 'Pacific/Noumea', offset: '+11:00' },
    { value: 'Pacific/Samoa', label: 'Pacific/Samoa', offset: '-11:00' },
    { value: 'Pacific/Tahiti', label: 'Pacific/Tahiti', offset: '-10:00' },
];

interface TimezoneSelectProps {
    value: string;
    onChange: (value: string) => void;
}

export function TimezoneSelect({ value, onChange }: TimezoneSelectProps) {
    const [open, setOpen] = useState(false);
    const [search, setSearch] = useState('');
    const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0, width: 0 });
    const containerRef = useRef<HTMLDivElement>(null);
    const dropdownRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLInputElement>(null);

    // Update dropdown position
    const updatePosition = useCallback(() => {
        if (containerRef.current) {
            const rect = containerRef.current.getBoundingClientRect();
            setDropdownPosition({
                top: rect.bottom + 4,
                left: rect.left,
                width: rect.width
            });
        }
    }, []);

    // Close on click outside
    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (
                containerRef.current && 
                !containerRef.current.contains(e.target as Node) &&
                dropdownRef.current &&
                !dropdownRef.current.contains(e.target as Node)
            ) {
                setOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    // Update position when opened and on scroll/resize
    useEffect(() => {
        if (open) {
            updatePosition();
            window.addEventListener('scroll', updatePosition, true);
            window.addEventListener('resize', updatePosition);
            return () => {
                window.removeEventListener('scroll', updatePosition, true);
                window.removeEventListener('resize', updatePosition);
            };
        }
    }, [open, updatePosition]);

    // Focus input when opened
    useEffect(() => {
        if (open && inputRef.current) {
            inputRef.current.focus();
        }
    }, [open]);

    const filteredTimezones = ALL_TIMEZONES.filter(tz => {
        const searchLower = search.toLowerCase();
        return (
            tz.value.toLowerCase().includes(searchLower) ||
            tz.label.toLowerCase().includes(searchLower) ||
            tz.offset.includes(search)
        );
    });

    const selectedTimezone = ALL_TIMEZONES.find(tz => tz.value === value);

    const dropdown = open && typeof document !== 'undefined' ? createPortal(
        <div 
            ref={dropdownRef}
            className="fixed z-[9999] bg-[#18181c] border border-[#27272a] rounded-lg shadow-xl overflow-hidden"
            style={{
                top: dropdownPosition.top,
                left: dropdownPosition.left,
                width: dropdownPosition.width,
            }}
        >
            {/* Search Input */}
            <div className="p-2 border-b border-[#27272a]">
                <div className="relative">
                    <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <input
                        ref={inputRef}
                        type="text"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        placeholder="Search timezone..."
                        className="w-full bg-[#09090b] text-white text-sm rounded py-1.5 pl-9 pr-3 border border-[#27272a] focus:border-emerald-500/50 focus:outline-none placeholder-muted-foreground"
                    />
                </div>
            </div>

            {/* Timezone List */}
            <div className="max-h-60 overflow-auto">
                {filteredTimezones.length === 0 ? (
                    <div className="py-4 text-center text-muted-foreground text-sm">
                        No timezone found
                    </div>
                ) : (
                    filteredTimezones.map((tz) => (
                        <button
                            key={tz.value}
                            type="button"
                            onClick={() => {
                                onChange(tz.value);
                                setOpen(false);
                                setSearch('');
                            }}
                            className={cn(
                                "w-full flex items-center justify-between px-3 py-2 text-sm hover:bg-white/5 transition-colors",
                                value === tz.value && "bg-emerald-500/10"
                            )}
                        >
                            <span className={cn("truncate", value === tz.value ? "text-emerald-400" : "text-white")}>
                                {tz.label}
                            </span>
                            <div className="flex items-center gap-2">
                                <span className="text-muted-foreground text-xs font-mono">UTC{tz.offset}</span>
                                {value === tz.value && <Check className="w-4 h-4 text-emerald-400" />}
                            </div>
                        </button>
                    ))
                )}
            </div>
        </div>,
        document.body
    ) : null;

    return (
        <div ref={containerRef} className="relative">
            <button
                type="button"
                onClick={() => setOpen(!open)}
                className="w-full bg-[#09090b] border border-white/5 text-white h-9 text-sm rounded px-3 flex items-center justify-between hover:border-white/10 transition-colors"
            >
                <span className="truncate">
                    {selectedTimezone ? `${selectedTimezone.label} (UTC${selectedTimezone.offset})` : 'Select timezone...'}
                </span>
                <ChevronDown className={cn("w-4 h-4 text-muted-foreground transition-transform", open && "rotate-180")} />
            </button>

            {dropdown}
        </div>
    );
}
