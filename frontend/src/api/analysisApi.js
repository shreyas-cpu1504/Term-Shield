import apiClient from "./client.js";

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

export async function getContractAnalysis(fileId) {
  const validId = validateContractId(fileId);
  const response = await apiClient.get(
    `/clauses/${encodeURIComponent(validId)}/analysis`
  );

  return response.data;
}

export async function getContractSummary(fileId) {
  const validId = validateContractId(fileId);
  const response = await apiClient.get(
    `/clauses/${encodeURIComponent(validId)}/summary`
  );

  return response.data;
}

export async function getContractClauses(fileId) {
  const validId = validateContractId(fileId);
  const response = await apiClient.get(
    `/clauses/${encodeURIComponent(validId)}`
  );

  return response.data;
}

export async function getContractRelationships(fileId) {
  const validId = validateContractId(fileId);
  const response = await apiClient.get(
    `/clauses/${encodeURIComponent(validId)}/relationships`
  );

  return response.data;
}