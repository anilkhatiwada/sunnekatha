"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import {
  Bell,
  Headphones,
  LogOut,
  Mail,
  Save,
  Settings2,
  UserRound,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { useAuth } from "@/features/auth/auth-provider";
import {
  type ProfilePreferencesFormValues,
  profilePreferencesSchema,
} from "@/features/profile/profile-schema";
import { usePreferencesStore } from "@/features/profile/preferences-store";
import { cn } from "@/lib/utils";
import { updateAccountPreferences, updateProfile } from "@/services";

const inputClassName =
  "mt-2 h-11 w-full rounded-lg border border-border bg-background/55 px-3 text-sm text-foreground transition-colors focus:border-primary focus:outline-2 focus:outline-primary disabled:cursor-not-allowed disabled:opacity-55";

export function ProfileSettingsPage() {
  const { user, refreshUser, logout } = useAuth();
  const preferences = usePreferencesStore();
  const updatePreferences = usePreferencesStore(
    (state) => state.updatePreferences,
  );
  const [statusMessage, setStatusMessage] = useState("");
  const hasHydrated = usePreferencesStore((state) => state.hasHydrated);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty, isSubmitting },
  } = useForm<ProfilePreferencesFormValues>({
    resolver: zodResolver(profilePreferencesSchema),
    defaultValues: {
      displayName: user?.displayName ?? "",
      email: user?.email ?? "",
      preferredLanguage: user?.preferredLanguage ?? preferences.preferredLanguage,
      autoplay: user?.autoplayEnabled ?? preferences.autoplay,
      defaultPlaybackSpeed:
        user?.defaultPlaybackSpeed ?? preferences.defaultPlaybackSpeed,
      allowExplicitContent:
        user?.explicitContentEnabled ?? preferences.allowExplicitContent,
      themePreference: preferences.themePreference,
    },
  });

  useEffect(() => {
    if (!hasHydrated) {
      return;
    }

    reset({
      displayName: user?.displayName ?? "",
      email: user?.email ?? "",
      preferredLanguage: user?.preferredLanguage ?? preferences.preferredLanguage,
      autoplay: user?.autoplayEnabled ?? preferences.autoplay,
      defaultPlaybackSpeed:
        user?.defaultPlaybackSpeed ?? preferences.defaultPlaybackSpeed,
      allowExplicitContent:
        user?.explicitContentEnabled ?? preferences.allowExplicitContent,
      themePreference: preferences.themePreference,
    });
  }, [
    hasHydrated,
    preferences.allowExplicitContent,
    preferences.autoplay,
    preferences.defaultPlaybackSpeed,
    preferences.displayName,
    preferences.email,
    preferences.preferredLanguage,
    preferences.themePreference,
    reset,
    user?.displayName,
    user?.email,
    user?.preferredLanguage,
    user?.autoplayEnabled,
    user?.defaultPlaybackSpeed,
    user?.explicitContentEnabled,
  ]);

  const savePreferences = async (values: ProfilePreferencesFormValues) => {
    setStatusMessage("");
    try {
      await Promise.all([
        updateProfile({ displayName: values.displayName, email: values.email }),
        updateAccountPreferences({
          preferredLanguage: values.preferredLanguage,
          defaultPlaybackSpeed: values.defaultPlaybackSpeed,
          autoplayEnabled: values.autoplay,
          explicitContentEnabled: values.allowExplicitContent,
        }),
      ]);
      updatePreferences(values);
      await refreshUser();
      reset(values);
      setStatusMessage("Your preferences were saved.");
    } catch {
      setStatusMessage("Changes could not be saved. Please try again.");
    }
  };

  return (
    <div className="space-y-10 pb-8">
      <header className="relative overflow-hidden rounded-2xl border border-border bg-surface/75 p-6 sm:p-8 lg:p-10">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgb(229_138_82_/_0.18),transparent_36rem)]" />
        <div className="relative flex flex-col gap-6 sm:flex-row sm:items-center">
          <div className="flex size-24 shrink-0 items-center justify-center rounded-full border border-primary/25 bg-primary/10 text-primary sm:size-28">
            <UserRound aria-hidden="true" className="size-11" />
          </div>
          <div>
            <p className="font-nepali text-xs font-semibold text-primary">
              Your space
            </p>
            <h1 className="mt-2 font-literary text-4xl font-semibold sm:text-5xl">
              {user?.displayName}
            </h1>
            <p className="mt-3 font-nepali text-sm text-muted-foreground">
              {user?.email}
            </p>
          </div>
        </div>
      </header>

      <form
        onSubmit={handleSubmit(savePreferences)}
        className="space-y-8"
        noValidate
      >
        <SettingsSection
          icon={UserRound}
          title="Profile"
          description="Your basic information shown on SunneKatha"
        >
          <div className="grid gap-5 sm:grid-cols-2">
            <FormField
              label="Name"
              error={errors.displayName?.message}
            >
              <input
                {...register("displayName")}
                autoComplete="name"
                className={inputClassName}
              />
            </FormField>
            <FormField label="Email" error={errors.email?.message}>
              <input
                {...register("email")}
                type="email"
                autoComplete="email"
                className={inputClassName}
              />
            </FormField>
          </div>
        </SettingsSection>

        <SettingsSection
          icon={Headphones}
          title="Listening preferences"
          description="Language, speed, and playback behavior"
        >
          <div className="grid gap-5 sm:grid-cols-2">
            <FormField label="Preferred language">
              <select
                {...register("preferredLanguage")}
                className={inputClassName}
              >
                <option value="ne">Nepali</option>
                <option value="en">English</option>
              </select>
            </FormField>
            <FormField label="Default playback speed">
              <select
                {...register("defaultPlaybackSpeed", {
                  valueAsNumber: true,
                })}
                className={inputClassName}
              >
                <option value={0.75}>0.75×</option>
                <option value={1}>1×</option>
                <option value={1.25}>1.25×</option>
                <option value={1.5}>1.5×</option>
                <option value={2}>2×</option>
              </select>
            </FormField>
          </div>

          <div className="mt-6 space-y-3">
            <ToggleField
              label="Autoplay"
              description="Automatically play the next track."
              registration={register("autoplay")}
            />
            <ToggleField
              label="Allow explicit content"
              description="Show content marked as explicit."
              registration={register("allowExplicitContent")}
            />
          </div>
        </SettingsSection>

        <SettingsSection
          icon={Settings2}
          title="Appearance"
          description="SunneKatha colors and system appearance"
        >
          <FormField label="Theme preference">
            <select
              {...register("themePreference")}
              className={cn(inputClassName, "max-w-md")}
            >
              <option value="dark">Dark</option>
              <option value="light">Light</option>
              <option value="system">System</option>
            </select>
          </FormField>
        </SettingsSection>

        <SettingsSection
          icon={Headphones}
          title="Audio quality"
          description="Streaming quality selection will be available in a future release."
        >
          <FormField label="Quality">
            <select
              disabled
              aria-describedby="audio-quality-note"
              className={cn(inputClassName, "max-w-md")}
              defaultValue="automatic"
            >
              <option value="automatic">Automatic · coming soon</option>
            </select>
          </FormField>
          <p
            id="audio-quality-note"
            className="mt-2 font-nepali text-xs text-muted-foreground"
          >
            Quality is currently selected automatically for your browser and available source.
          </p>
        </SettingsSection>

        <SettingsSection
          icon={Bell}
          title="Notifications"
          description="Notifications for new tracks and recommendations"
        >
          <div className="space-y-3">
            <PlaceholderPreference
              icon={Mail}
              label="Email Notifications"
              description="Weekly new-release summary · coming soon"
            />
            <PlaceholderPreference
              icon={Bell}
              label="Push notifications"
              description="New tracks from favorite creators · coming soon"
            />
          </div>
        </SettingsSection>

        <div className="sticky bottom-[calc(10rem+env(safe-area-inset-bottom))] z-10 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-background/90 p-3 shadow-xl backdrop-blur lg:bottom-[6.5rem]">
          <p
            role="status"
            aria-live="polite"
            className="min-h-5 font-nepali text-xs text-muted-foreground"
          >
            {statusMessage}
          </p>
          <Button
            type="submit"
            disabled={isSubmitting || !isDirty}
            className="rounded-full font-nepali"
          >
            <Save aria-hidden="true" className="size-4" />
            Save preferences
          </Button>
        </div>
      </form>

      {user?.isCreator ? (
        <section className="rounded-2xl border border-primary/20 bg-primary/5 p-6">
          <h2 className="font-literary text-2xl font-semibold">Creator Center</h2>
          <p className="mt-2 font-nepali text-sm text-muted-foreground">
            Upload original audio and editorial images directly to secure storage.
          </p>
          <Link
            href="/creator"
            className="mt-4 inline-flex min-h-11 items-center rounded-full bg-primary px-5 py-2 font-nepali text-sm font-semibold text-background"
          >
            Open Creator Center
          </Link>
        </section>
      ) : null}

      <section className="rounded-2xl border border-border bg-surface/55 p-6">
        <h2 className="font-literary text-2xl font-semibold">Listening activity</h2>
        <p className="mt-2 font-nepali text-sm text-muted-foreground">
          View recently played tracks, play counts, and total listening time.
        </p>
        <Link
          href="/history"
          className="mt-4 inline-flex min-h-11 items-center rounded-full border border-border px-5 py-2 font-nepali text-sm font-semibold hover:border-primary/50"
        >
          Open listening history
        </Link>
      </section>

      <section className="rounded-2xl border border-destructive/20 bg-destructive/5 p-6">
        <h2 className="font-literary text-2xl font-semibold">Account</h2>
        <p className="mt-2 font-nepali text-sm text-muted-foreground">
          Sign out securely from this device.
        </p>
        <Button
          type="button"
          variant="ghost"
          onClick={() => {
            void logout().finally(() => window.location.assign("/login"));
          }}
          className="mt-4 rounded-full font-nepali text-destructive"
        >
          <LogOut aria-hidden="true" className="size-4" />
          Sign out
        </Button>
      </section>
    </div>
  );
}

function SettingsSection({
  icon,
  title,
  description,
  children,
}: {
  icon: typeof Settings2;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  const headingId = `${title.replaceAll(" ", "-")}-heading`;
  return (
    <section
      aria-labelledby={headingId}
      className="rounded-2xl border border-border bg-surface/55 p-5 sm:p-7"
    >
      <SectionHeading
        id={headingId}
        icon={icon}
        title={title}
        description={description}
      />
      <div className="mt-6">{children}</div>
    </section>
  );
}

function SectionHeading({
  id,
  icon: Icon,
  title,
  description,
}: {
  id: string;
  icon: typeof Settings2;
  title: string;
  description: string;
}) {
  return (
    <div className="flex items-start gap-3">
      <span className="mt-0.5 inline-flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
        <Icon aria-hidden="true" className="size-4" />
      </span>
      <div>
        <h2 id={id} className="font-literary text-2xl font-semibold">
          {title}
        </h2>
        <p className="mt-1 font-nepali text-sm text-muted-foreground">
          {description}
        </p>
      </div>
    </div>
  );
}

function FormField({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block font-nepali text-sm font-medium">
      {label}
      {children}
      {error && (
        <span className="mt-1.5 block text-xs text-destructive">
          {error}
        </span>
      )}
    </label>
  );
}

function ToggleField({
  label,
  description,
  registration,
}: {
  label: string;
  description: string;
  registration: ReturnType<
    ReturnType<typeof useForm<ProfilePreferencesFormValues>>["register"]
  >;
}) {
  return (
    <label className="flex cursor-pointer items-center justify-between gap-5 rounded-xl border border-border bg-background/35 p-4">
      <span>
        <span className="block font-nepali text-sm font-semibold">
          {label}
        </span>
        <span className="mt-1 block font-nepali text-xs leading-5 text-muted-foreground">
          {description}
        </span>
      </span>
      <input
        type="checkbox"
        {...registration}
        className="size-5 shrink-0 accent-primary"
      />
    </label>
  );
}

function PlaceholderPreference({
  icon: Icon,
  label,
  description,
}: {
  icon: typeof Bell;
  label: string;
  description: string;
}) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-xl border border-border bg-background/35 p-4 opacity-70">
      <div className="flex items-center gap-3">
        <Icon aria-hidden="true" className="size-4 text-primary" />
        <div>
          <p className="font-nepali text-sm font-semibold">{label}</p>
          <p className="mt-1 font-nepali text-xs text-muted-foreground">
            {description}
          </p>
        </div>
      </div>
      <input
        type="checkbox"
        disabled
        aria-label={`${label} coming soon`}
        className="size-5 shrink-0"
      />
    </div>
  );
}
