import type { Metadata } from "next";

import { AuthRequired } from "@/features/auth/auth-required";
import { NotificationsPageContent } from "@/features/notifications/notifications-page";

export const metadata: Metadata = { title: "Notifications" };

export default function NotificationsPage() {
  return (
    <AuthRequired>
      <NotificationsPageContent />
    </AuthRequired>
  );
}
