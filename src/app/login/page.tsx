import type { Metadata } from "next";

import { GoogleSignIn } from "@/features/auth/google-sign-in";

export const metadata: Metadata = { title: "साइन इन" };

export default function LoginPage() {
  return (
    <div className="mx-auto flex min-h-[65vh] max-w-lg items-center">
      <section className="w-full rounded-2xl border border-border bg-surface p-6 text-center sm:p-10">
        <p className="font-nepali text-sm font-medium text-primary">
          SunneKatha
        </p>
        <h1 className="mt-3 font-literary text-3xl font-semibold">
          आफ्नो खातामा साइन इन गर्नुहोस्
        </h1>
        <p className="mt-3 mb-8 font-nepali leading-7 text-muted-foreground">
          आफ्नो पुस्तकालय, सुन्ने प्रगति र प्लेलिस्ट सुरक्षित राख्न Google
          खाता प्रयोग गर्नुहोस्।
        </p>
        <GoogleSignIn />
      </section>
    </div>
  );
}
