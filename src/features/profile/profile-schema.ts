import { z } from "zod";

export const profilePreferencesSchema = z.object({
  displayName: z
    .string()
    .trim()
    .min(2, "Name must be at least 2 characters.")
    .max(50, "Name cannot exceed 50 characters."),
  email: z.email("Enter a valid email address."),
  preferredLanguage: z.enum(["ne", "en"]),
  autoplay: z.boolean(),
  defaultPlaybackSpeed: z.number().min(0.5).max(2),
  allowExplicitContent: z.boolean(),
  themePreference: z.enum(["dark", "light", "system"]),
});

export type ProfilePreferencesFormValues = z.infer<
  typeof profilePreferencesSchema
>;
