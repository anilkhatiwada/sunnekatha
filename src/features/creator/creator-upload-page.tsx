"use client";

import { FileAudio, FileImage, UploadCloud } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/features/auth/auth-provider";
import { ApiError, uploadCreatorFile, type UploadType } from "@/services";
import type { ApiUploadSession } from "@/types";

const uploadOptions = [
  {
    value: "audio_master",
    label: "Original audio",
    accept: "audio/mpeg,audio/wav,audio/x-wav,audio/flac,audio/mp4,audio/x-m4a",
    icon: FileAudio,
  },
  {
    value: "cover_image",
    label: "Cover image",
    accept: "image/jpeg,image/png,image/webp",
    icon: FileImage,
  },
  {
    value: "author_image",
    label: "Author image",
    accept: "image/jpeg,image/png,image/webp",
    icon: FileImage,
  },
  {
    value: "narrator_image",
    label: "Narrator image",
    accept: "image/jpeg,image/png,image/webp",
    icon: FileImage,
  },
] as const;

export function CreatorUploadPage() {
  const { user } = useAuth();
  const [uploadType, setUploadType] = useState<UploadType>("audio_master");
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [completed, setCompleted] = useState<ApiUploadSession | null>(null);
  const [message, setMessage] = useState("");
  const option = uploadOptions.find((item) => item.value === uploadType)!;

  if (!user?.isCreator) {
    return (
      <section className="rounded-2xl border border-border bg-surface p-7">
        <h1 className="font-literary text-3xl font-semibold">Creator upload</h1>
        <p className="mt-3 font-nepali leading-7 text-muted-foreground">
          Uploads are limited to approved creators and staff. Contact the
          SunneKatha editorial team for access.
        </p>
      </section>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-7">
      <header>
        <p className="font-nepali text-sm font-semibold text-primary">
          Creator Center
        </p>
        <h1 className="mt-2 font-literary text-4xl font-semibold">
          Secure file upload
        </h1>
        <p className="mt-3 max-w-2xl font-nepali leading-7 text-muted-foreground">
          Files go directly to secure storage. Editorial review and processing start separately after upload.
        </p>
      </header>

      <form
        className="space-y-6 rounded-2xl border border-border bg-surface/70 p-6"
        onSubmit={(event) => {
          event.preventDefault();
          if (!file) return;
          const form = event.currentTarget;
          setIsUploading(true);
          setMessage("");
          setCompleted(null);
          void uploadCreatorFile(file, uploadType)
            .then((session) => {
              setCompleted(session);
              setMessage("The file was uploaded and confirmed.");
              setFile(null);
              form.reset();
            })
            .catch((error: unknown) => {
              setMessage(
                error instanceof ApiError
                  ? error.message
                  : "Upload failed. Check the file type and size.",
              );
            })
            .finally(() => setIsUploading(false));
        }}
      >
        <fieldset>
          <legend className="font-nepali text-sm font-semibold">
            File type
          </legend>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            {uploadOptions.map(({ value, label, icon: Icon }) => (
              <label
                key={value}
                className={`flex cursor-pointer items-center gap-3 rounded-xl border p-4 font-nepali text-sm ${
                  uploadType === value
                    ? "border-primary bg-primary/10"
                    : "border-border bg-background/35"
                }`}
              >
                <input
                  type="radio"
                  name="uploadType"
                  value={value}
                  checked={uploadType === value}
                  onChange={() => {
                    setUploadType(value);
                    setFile(null);
                  }}
                />
                <Icon aria-hidden="true" className="size-5 text-primary" />
                {label}
              </label>
            ))}
          </div>
        </fieldset>

        <label className="block font-nepali text-sm font-semibold">
          {option.label} — choose file
          <input
            key={uploadType}
            type="file"
            required
            accept={option.accept}
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            className="mt-3 block w-full rounded-xl border border-dashed border-border bg-background/40 p-5 text-sm file:mr-4 file:rounded-full file:border-0 file:bg-primary file:px-4 file:py-2 file:font-nepali file:font-semibold file:text-background"
          />
        </label>

        {file ? (
          <p className="font-nepali text-sm text-muted-foreground">
            {file.name} · {(file.size / 1024 / 1024).toFixed(2)} MB
          </p>
        ) : null}

        <Button
          type="submit"
          disabled={!file || isUploading}
          className="rounded-full font-nepali"
        >
          <UploadCloud aria-hidden="true" className="size-4" />
          {isUploading ? "Uploading…" : "Start secure upload"}
        </Button>

        <p
          role={completed ? "status" : "alert"}
          aria-live="polite"
          className="min-h-5 font-nepali text-sm text-muted-foreground"
        >
          {message}
        </p>
      </form>

      {completed ? (
        <section className="rounded-xl border border-primary/25 bg-primary/5 p-5">
          <h2 className="font-nepali font-semibold">Upload confirmed</h2>
          <p className="mt-2 font-nepali text-sm text-muted-foreground">
            {completed.originalFilename} · {completed.status}
          </p>
        </section>
      ) : null}
    </div>
  );
}
