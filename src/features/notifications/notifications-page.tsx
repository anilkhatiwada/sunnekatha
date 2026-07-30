"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, CheckCheck } from "lucide-react";
import Link from "next/link";

import { EmptyState } from "@/components/common/empty-state";
import { LoadingSkeleton } from "@/components/common/loading-skeleton";
import { SectionError } from "@/components/common/section-error";
import { Button } from "@/components/ui/button";
import {
  getNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  queryKeys,
} from "@/services";

export function NotificationsPageContent() {
  const queryClient = useQueryClient();
  const notifications = useQuery({
    queryKey: queryKeys.notifications.list(),
    queryFn: getNotifications,
    staleTime: 15_000,
  });
  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({
        queryKey: queryKeys.notifications.list(),
      }),
      queryClient.invalidateQueries({
        queryKey: queryKeys.notifications.unread(),
      }),
    ]);
  const readMutation = useMutation({
    mutationFn: markNotificationRead,
    onSuccess: refresh,
  });
  const readAllMutation = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: refresh,
  });

  if (notifications.isError) {
    return (
      <SectionError
        message="सूचनाहरू लोड गर्न सकिएन।"
        onRetry={() => void notifications.refetch()}
        isRetrying={notifications.isFetching}
      />
    );
  }

  return (
    <div className="space-y-8 pb-8">
      <header className="flex flex-wrap items-end justify-between gap-5 rounded-2xl border border-border bg-surface/70 p-7 sm:p-9">
        <div>
          <p className="font-nepali text-xs font-semibold text-primary">
            तपाईंका अपडेट
          </p>
          <h1 className="mt-2 font-literary text-4xl font-semibold">
            सूचनाहरू
          </h1>
        </div>
        <Button
          type="button"
          variant="secondary"
          disabled={
            readAllMutation.isPending ||
            !notifications.data?.some((item) => !item.isRead)
          }
          onClick={() => readAllMutation.mutate()}
          className="rounded-full font-nepali"
        >
          <CheckCheck aria-hidden="true" className="size-4" />
          सबै पढिएको चिन्ह लगाउनुहोस्
        </Button>
      </header>

      {notifications.isPending ? (
        <div className="space-y-3">
          {Array.from({ length: 6 }, (_, index) => (
            <LoadingSkeleton key={index} className="h-28 rounded-xl" />
          ))}
        </div>
      ) : notifications.data.length ? (
        <ol className="space-y-3">
          {notifications.data.map((notification) => (
            <li
              key={notification.id}
              className={`rounded-xl border p-5 ${
                notification.isRead
                  ? "border-border bg-surface/45"
                  : "border-primary/30 bg-primary-muted/10"
              }`}
            >
              <div className="flex items-start gap-4">
                <span className="grid size-10 shrink-0 place-items-center rounded-full bg-primary-muted/30 text-primary">
                  <Bell aria-hidden="true" className="size-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <h2 className="font-nepali font-semibold">
                    {notification.title}
                  </h2>
                  <p className="mt-1 font-nepali text-sm leading-6 text-muted-foreground">
                    {notification.message}
                  </p>
                  <p className="mt-2 text-xs text-muted-foreground">
                    {new Intl.DateTimeFormat("ne-NP", {
                      dateStyle: "medium",
                      timeStyle: "short",
                    }).format(new Date(notification.createdAt))}
                  </p>
                </div>
                <div className="flex shrink-0 flex-col gap-2">
                  {notification.actionUrl ? (
                    <Button asChild size="sm" variant="ghost">
                      <Link href={notification.actionUrl}>हेर्नुहोस्</Link>
                    </Button>
                  ) : null}
                  {!notification.isRead ? (
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      disabled={readMutation.isPending}
                      onClick={() => readMutation.mutate(notification.id)}
                      className="font-nepali"
                    >
                      पढियो
                    </Button>
                  ) : null}
                </div>
              </div>
            </li>
          ))}
        </ol>
      ) : (
        <EmptyState
          icon={Bell}
          title="नयाँ सूचना छैन"
          description="सर्जक, प्लेलिस्ट र खातासम्बन्धी अपडेट यहाँ देखिनेछन्।"
        />
      )}
    </div>
  );
}
