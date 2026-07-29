import { ErrorState } from "@/components/common/error-state";

interface SectionErrorProps {
  message?: string;
  onRetry?: () => void;
  isRetrying?: boolean;
}

export function SectionError({
  message = "यो सामग्री अहिले उपलब्ध हुन सकेन।",
  onRetry,
  isRetrying,
}: SectionErrorProps) {
  return (
    <ErrorState
      compact
      message={message}
      onRetry={onRetry}
      isRetrying={isRetrying}
    />
  );
}
