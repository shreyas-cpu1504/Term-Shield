import axios from "axios";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api/v1",
  timeout: 120000,
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("termShieldToken");

  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("termShieldToken");
    }

    return Promise.reject(error);
  }
);

export default apiClient;