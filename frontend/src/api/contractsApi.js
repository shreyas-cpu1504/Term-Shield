import apiClient from "./client";

export async function getContracts() {
  const response = await apiClient.get(
    "/contracts"
  );

  return response.data;
}
