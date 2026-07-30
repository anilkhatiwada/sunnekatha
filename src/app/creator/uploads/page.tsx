import type { Metadata } from "next";

import { AuthRequired } from "@/features/auth/auth-required";
import { CreatorUploadPage } from "@/features/creator/creator-upload-page";

export const metadata: Metadata = { title: "सर्जक फाइल अपलोड" };

export default function CreatorUploadsRoute() {
  return (
    <AuthRequired>
      <CreatorUploadPage />
    </AuthRequired>
  );
}
