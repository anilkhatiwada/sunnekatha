import type { Metadata } from "next";

import { AuthRequired } from "@/features/auth/auth-required";
import { ListeningHistoryPage } from "@/features/library/listening-history-page";

export const metadata: Metadata = { title: "Listening History" };

export default function HistoryRoute() {
  return (
    <AuthRequired>
      <ListeningHistoryPage />
    </AuthRequired>
  );
}
