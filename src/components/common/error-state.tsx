import { CircleAlert, RotateCcw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  isRetrying?: boolean;
  compact?: boolean;
  className?: string;
}

export function ErrorState({
  title = "केही समस्या भयो",
  message = "यो सामग्री अहिले ल्याउन सकिएन। केही बेरपछि फेरि प्रयास गर्नुहोस्।",
  onRetry,
  isRetrying = false,
  compact = false,
  className,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(
        "grid place-items-center rounded-xl border border-danger/30 bg-danger/5 px-6 text-center",
        compact ? "min-h-32 py-6" : "min-h-56 py-10",
        className,
      )}
    >
      <div className="max-w-md">
        <div className="mx-auto grid size-11 place-items-center rounded-full bg-danger/10 text-danger">
          <CircleAlert aria-hidden="true" className="size-5" />
        </div>
        <h2 className="mt-3 font-literary text-lg font-semibold text-foreground">
          {title}
        </h2>
        <p className="mt-1.5 font-nepali text-sm leading-6 text-muted-foreground">
          {message}
        </p>
        {onRetry ? (
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={onRetry}
            disabled={isRetrying}
            className="mt-4 min-h-11 gap-2 rounded-full font-nepali"
          >
            <RotateCcw
              aria-hidden="true"
              className={cn("size-4", isRetrying && "animate-spin")}
            />
            {isRetrying ? "फेरि प्रयास हुँदैछ…" : "फेरि प्रयास गर्नुहोस्"}
          </Button>
        ) : null}
      </div>
    </div>
  );
}
