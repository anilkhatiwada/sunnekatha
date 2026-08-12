import type { Metadata } from "next";

import { AuthRequired } from "@/features/auth/auth-required";
import { CreatorCenterPage } from "@/features/creator/creator-center-page";

export const metadata: Metadata = { title: "Creator Center" };

export default function CreatorRoute() {
  return (
    <AuthRequired>
      <CreatorCenterPage />
    </AuthRequired>
  );
}
