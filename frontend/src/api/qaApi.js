import apiClient from "./client";

export async function askContractQuestion(fileId, question) {
  const response = await apiClient.post(
    `/qa/${fileId}`,
    { question }
  );

  return response.data;
}

export async function getQAHistory(fileId) {
  const response = await apiClient.get(`/qa/${fileId}/history`);
  return response.data;
}