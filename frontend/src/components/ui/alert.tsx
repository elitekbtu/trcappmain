import { cn } from "../../lib/utils"
import  type { ReactNode } from "react"

type AlertProps = {
  variant?: 'default' | 'destructive'
  children: ReactNode
  className?: string
}

export const Alert = ({ 
  variant = 'default', 
  children,
  className 
}: AlertProps) => {
  return (
    <div
      className={cn(
        "relative rounded-lg border p-4",
        variant === 'destructive' && 
          "border-red-200 bg-red-50 text-red-600 dark:border-red-800 dark:bg-red-950 dark:text-red-400",
        className
      )}
    >
      {children}
    </div>
  )
}

export const AlertTitle = ({ 
  children,
  className 
}: { children: ReactNode, className?: string }) => {
  return (
    <h5 className={cn("mb-1 font-medium leading-none tracking-tight", className)}>
      {children}
    </h5>
  )
}

export const AlertDescription = ({ 
  children,
  className 
}: { children: ReactNode, className?: string }) => {
  return (
    <div className={cn("mt-2 text-sm", className)}>
      {children}
    </div>
  )
}