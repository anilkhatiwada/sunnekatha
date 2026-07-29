import { z } from "zod";

export const profilePreferencesSchema = z.object({
  displayName: z
    .string()
    .trim()
    .min(2, "नाम कम्तीमा २ अक्षरको हुनुपर्छ।")
    .max(50, "नाम ५० अक्षरभन्दा लामो हुन सक्दैन।"),
  email: z.email("मान्य इमेल ठेगाना लेख्नुहोस्।"),
  preferredLanguage: z.enum(["ne", "en"]),
  autoplay: z.boolean(),
  defaultPlaybackSpeed: z.number().min(0.5).max(2),
  allowExplicitContent: z.boolean(),
  themePreference: z.enum(["dark", "light", "system"]),
});

export type ProfilePreferencesFormValues = z.infer<
  typeof profilePreferencesSchema
>;
