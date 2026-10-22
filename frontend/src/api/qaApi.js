import apiClient from "./client";

export function validateContractId(fileId) {
  if (
    fileId === undefined ||
    fileId === null ||
    fileId === "undefined" ||
    fileId === "null" ||
    (typeof fileId === "string" && fileId.trim() === "")
  ) {
    throw new Error("Invalid contract ID: Contract ID must not be null, undefined, or empty.");
  }
  return String(fileId).trim();
}

export async function askContractQuestion(fileId, question, language = null) {
  const validId = validateContractId(fileId);
  const payload = { question };
  if (language && typeof language === "string" && language.trim()) {
    payload.language = language.trim();
  }
  const response = await apiClient.post(
    `/qa/${encodeURIComponent(validId)}`,
    payload
  );

  return response.data;
}

export async function getQAHistory(fileId) {
  const validId = validateContractId(fileId);
  const response = await apiClient.get(`/qa/${encodeURIComponent(validId)}/history`);
  return response.data;
}

export async function clearQAHistory(fileId) {
  const validId = validateContractId(fileId);
  const response = await apiClient.delete(`/qa/${encodeURIComponent(validId)}/history`);
  return response.data;
}