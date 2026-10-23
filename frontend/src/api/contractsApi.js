import apiClient from "./client.js";

export async function getContracts(options = {}) {
  const response = await apiClient.get(
    "/contracts",
    {
      headers: {
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        ...(options?.headers || {}),
      },
      params: options?.params,
    }
  );

  return response.data;
}

export async function deleteContract(contractId) {
  const response = await apiClient.delete(
    `/contracts/${contractId}`
  );

  return response.data;
}
