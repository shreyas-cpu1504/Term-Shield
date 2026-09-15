import apiClient from "./client";

export async function getContractAnalysis(fileId) {
  const response = await apiClient.get(
    `/clauses/${fileId}/analysis`
  );

  return response.data;
}

export async function getContractSummary(fileId) {
  const response = await apiClient.get(
    `/clauses/${fileId}/summary`
  );

  return response.data;
}

export async function getContractClauses(fileId) {
  const response = await apiClient.get(
    `/clauses/${fileId}`
  );

  return response.data;
}

export async function getContractRelationships(fileId) {
  const response = await apiClient.get(
    `/clauses/${fileId}/relationships`
  );

  return response.data;
}