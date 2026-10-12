import * as React from "react"
import { cn } from "@/lib/utils"

type AlertVariant = 'default' | 'destructive' | 'warning' | 'success';

const variantStyles: Record<AlertVariant, string> = {
    default: "bg-background text-foreground border-border",
    destructive: "bg-red-500/10 border-red-500/20 text-red-500",
    warning: "bg-yellow-500/10 border-yellow-500/20 text-yellow-500",
    success: "bg-green-500/10 border-green-500/20 text-green-500",
};

interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
    variant?: AlertVariant;
}

const Alert = React.forwardRef<HTMLDivElement, AlertProps>(
    ({ className, variant = 'default', ...props }, ref) => (
        <div
            ref={ref}
            role="alert"
            className={cn("relative w-full rounded-lg border p-4", variantStyles[variant], className)}
            {...props}
        />
    )
)
Alert.displayName = "Alert"

const AlertTitle = React.forwardRef<
    HTMLParagraphElement,
    React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
    <h5
        ref={ref}
        className={cn("mb-1 font-medium leading-none tracking-tight", className)}
        {...props}
    />
))
AlertTitle.displayName = "AlertTitle"

const AlertDescription = React.forwardRef<
    HTMLParagraphElement,
    React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
    <div
        ref={ref}
        className={cn("text-sm [&_p]:leading-relaxed", className)}
        {...props}
    />
))
AlertDescription.displayName = "AlertDescription"

export { Alert, AlertTitle, AlertDescription }
