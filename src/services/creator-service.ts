import { apiClient } from "@/services/api-client";
import type {
  ApiCreatorProfile,
  ApiCreatorTrack,
  ApiCreatorTrackPage,
  ApiCreatorUploadPage,
} from "@/types";

export function getCreatorProfile() {
  return apiClient.get<ApiCreatorProfile>("/creator/profile/", {
    requiresAuth: true,
  });
}

export function updateCreatorProfile(input: {
  displayName: string;
  biography: string;
  roles: ApiCreatorProfile["roles"];
}) {
  return apiClient.patch<ApiCreatorProfile, typeof input>(
    "/creator/profile/",
    { body: input, requiresAuth: true },
  );
}

export function getCreatorDrafts() {
  return apiClient.get<ApiCreatorTrackPage>("/creator/tracks/drafts/", {
    query: { pageSize: 50 },
    requiresAuth: true,
  });
}

export function getCreatorUploads() {
  return apiClient.get<ApiCreatorUploadPage>("/creator/uploads/", {
    query: { pageSize: 50 },
    requiresAuth: true,
  });
}

export function submitCreatorTrack(slug: string) {
  return apiClient.post<{
    id: string;
    slug: string;
    processingStatus: string;
    reviewStatus: string;
  }>(`/creator/tracks/${slug}/submit/`, { requiresAuth: true });
}

export function updateCreatorDraft(
  slug: string,
  input: {
    titleNe?: string;
    titleEn?: string;
    descriptionNe?: string;
    descriptionEn?: string;
    chapterNumber?: number | null;
    trackNumber?: number | null;
    isExplicit?: boolean;
  },
) {
  return apiClient.patch<ApiCreatorTrack, typeof input>(
    `/creator/tracks/${slug}/metadata/`,
    { body: input, requiresAuth: true },
  );
}
