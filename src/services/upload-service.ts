import { apiClient } from "@/services/api-client";
import type { ApiUploadSession, ApiUploadURLResponse } from "@/types";

export type UploadType =
  | "audio_master"
  | "cover_image"
  | "narrator_image"
  | "author_image";

export interface UploadRequest extends Record<string, unknown> {
  uploadType: UploadType;
  originalFilename: string;
  contentType: string;
  expectedSize: number;
}

export function requestDirectUpload(input: UploadRequest) {
  return apiClient.post<ApiUploadURLResponse, UploadRequest>("/uploads/", {
    body: input,
    requiresAuth: true,
  });
}

export async function uploadFileDirectly(
  instructions: ApiUploadURLResponse["upload"],
  file: File,
) {
  const body = new FormData();
  for (const [key, value] of Object.entries(instructions.fields)) {
    body.append(key, value);
  }
  body.append("file", file);

  const response = await fetch(instructions.url, { method: "POST", body });
  if (!response.ok) {
    throw new Error(`Direct upload failed with status ${response.status}.`);
  }
}

export function confirmDirectUpload(sessionId: string) {
  return apiClient.post<ApiUploadSession>(
    `/uploads/${sessionId}/confirm/`,
    { requiresAuth: true },
  );
}

export function cancelDirectUpload(sessionId: string) {
  return apiClient.post<ApiUploadSession>(
    `/uploads/${sessionId}/cancel/`,
    { requiresAuth: true },
  );
}

export function getUploadStatus(sessionId: string) {
  return apiClient.get<ApiUploadSession>(`/uploads/${sessionId}/`, {
    requiresAuth: true,
  });
}

export async function uploadCreatorFile(file: File, uploadType: UploadType) {
  const session = await requestDirectUpload({
    uploadType,
    originalFilename: file.name,
    contentType: file.type,
    expectedSize: file.size,
  });

  try {
    await uploadFileDirectly(session.upload, file);
    return await confirmDirectUpload(session.id);
  } catch (error) {
    await cancelDirectUpload(session.id).catch(() => undefined);
    throw error;
  }
}
