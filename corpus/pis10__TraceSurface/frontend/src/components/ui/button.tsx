import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "group inline-flex max-w-full items-center justify-center gap-2 overflow-hidden whitespace-nowrap rounded-md text-[12px] font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-45",
  {
    variants: {
      variant: {
        default: "border border-brand bg-[linear-gradient(180deg,var(--brand),var(--brand-dim))] text-white shadow-[0_6px_18px_var(--brand-glow)] hover:border-[var(--brand-dim)] hover:brightness-105",
        ghost: "border border-transparent bg-transparent text-text-3 hover:border-line-2 hover:bg-ink-2 hover:text-text",
        outline: "border border-line-2 bg-transparent text-text-2 hover:border-brand hover:bg-[var(--brand-soft)] hover:text-brand",
        subtle: "border border-line-2 bg-surface-content text-text-2 hover:border-line-2 hover:bg-ink-2 hover:text-text",
        danger: "border border-red bg-[var(--red-soft)] text-red hover:bg-red hover:text-white",
      },
      size: {
        sm: "h-7 px-2.5",
        md: "h-8 px-3",
        icon: "h-8 w-8 p-0",
      },
    },
    defaultVariants: {
      variant: "outline",
      size: "md",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return <Comp ref={ref} className={cn(buttonVariants({ variant, size, className }))} {...props} />;
  },
);
Button.displayName = "Button";
