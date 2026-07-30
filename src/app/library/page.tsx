import type { Metadata } from "next";

import { AuthRequired } from "@/features/auth/auth-required";
import { LibraryPageContent } from "@/features/library/library-page";

export const metadata: Metadata = {
  title: "लाइब्रेरी",
  description: "तपाईंका सुरक्षित र मनपर्ने SunneKatha सामग्री।",
};

export default function LibraryPage() {
  return (
    <AuthRequired>
      <LibraryPageContent />
    </AuthRequired>
  );
}
