import apiClient from "./client";

export async function uploadContractFile(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await apiClient.post("/ingestion/file", formData);

  return response.data;
}

export async function uploadContractAudio(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await apiClient.post("/ingestion/audio", formData);

  return response.data;
}

export async function uploadContractVideo(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await apiClient.post("/ingestion/video", formData);

  return response.data;
}

export async function ingestContractUrl(url) {
  const response = await apiClient.post("/ingestion/url", {
    url,
  });

  return response.data;
}