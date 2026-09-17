import apiClient from "./client";

export async function getContracts() {
  const response = await apiClient.get(
    "/contracts"
  );

  return response.data;
}

export async function deleteContract(contractId) {
  const response = await apiClient.delete(
    `/contracts/${contractId}`
  );

  return response.data;
}
