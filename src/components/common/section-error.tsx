import { ErrorState } from "@/components/common/error-state";

interface SectionErrorProps {
  message?: string;
  onRetry?: () => void;
  isRetrying?: boolean;
}

export function SectionError({
  message = "This content is currently unavailable.",
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
