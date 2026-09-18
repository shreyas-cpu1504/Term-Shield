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

export async function getAuthProviders() {
  const response = await apiClient.get(
    "/auth/providers"
  );

  return response.data;
}

export function getOAuthLoginUrl(provider) {
  const baseUrl = (apiClient.defaults.baseURL || "http://127.0.0.1:8000/api/v1").replace(/\/+$/, "");
  return `${baseUrl}/auth/${provider}/login`;
}

export async function exchangeOAuthCode(code) {
  const response = await apiClient.post(
    "/auth/oauth/exchange",
    { code }
  );

  return response.data;
}
