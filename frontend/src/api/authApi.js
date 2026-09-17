import apiClient from "./client";

export async function registerUser(data) {
  const response = await apiClient.post(
    "/auth/register",
    data
  );

  return response.data;
}

export async function loginUser(data) {
  const response = await apiClient.post(
    "/auth/login",
    data
  );

  return response.data;
}

export async function getCurrentUser() {
  const response = await apiClient.get(
    "/auth/me"
  );

  return response.data;
}
