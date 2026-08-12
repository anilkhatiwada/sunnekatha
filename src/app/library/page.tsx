import type { Metadata } from "next";

import { AuthRequired } from "@/features/auth/auth-required";
import { LibraryPageContent } from "@/features/library/library-page";

export const metadata: Metadata = {
  title: "Library",
  description: "Your saved and favorite SunneKatha content.",
};

export default function LibraryPage() {
  return (
    <AuthRequired>
      <LibraryPageContent />
    </AuthRequired>
  );
}
