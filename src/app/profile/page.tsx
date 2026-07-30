import type { Metadata } from "next";

import { ProfileSettingsPage } from "@/features/profile/profile-settings-page";
import { AuthRequired } from "@/features/auth/auth-required";

export const metadata: Metadata = {
  title: "प्रोफाइल र सेटिङ",
  description: "SunneKatha प्रोफाइल र श्रवण प्राथमिकताहरू व्यवस्थापन गर्नुहोस्।",
};

export default function ProfilePage() {
  return (
    <AuthRequired>
      <ProfileSettingsPage />
    </AuthRequired>
  );
}
