import type { Metadata } from "next";

import { ProfileSettingsPage } from "@/features/profile/profile-settings-page";
import { AuthRequired } from "@/features/auth/auth-required";

export const metadata: Metadata = {
  title: "Profile & Settings",
  description: "Manage your SunneKatha profile and listening preferences.",
};

export default function ProfilePage() {
  return (
    <AuthRequired>
      <ProfileSettingsPage />
    </AuthRequired>
  );
}
