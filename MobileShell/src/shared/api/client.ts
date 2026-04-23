import axios from "axios";
import { API_BASE_URL } from "../config";
import { Tokens } from "../types";

type TokenAccessors = {
  getTokens: () => Tokens | null;
  setTokens: (tokens: Tokens | null) => Promise<void>;
};

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

let tokenAccessors: TokenAccessors | null = null;
let refreshInFlight: Promise<Tokens | null> | null = null;

export function configureApiAuth(accessors: TokenAccessors) {
  tokenAccessors = accessors;
}

api.interceptors.request.use((config) => {
  const tokens = tokenAccessors?.getTokens();
  if (tokens?.access) {
    config.headers.Authorization = `Bearer ${tokens.access}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as any;
    if (!tokenAccessors || !originalRequest || originalRequest._retry || error.response?.status !== 401) {
      return Promise.reject(error);
    }

    const current = tokenAccessors.getTokens();
    if (!current?.refresh) {
      return Promise.reject(error);
    }

    if (!refreshInFlight) {
      refreshInFlight = api
        .post<Tokens>("/auth/token/refresh/", { refresh: current.refresh })
        .then((res) => res.data)
        .catch(() => null)
        .finally(() => {
          refreshInFlight = null;
        });
    }

    const refreshed = await refreshInFlight;
    if (!refreshed?.access) {
      await tokenAccessors.setTokens(null);
      return Promise.reject(error);
    }

    const merged: Tokens = { access: refreshed.access, refresh: current.refresh };
    await tokenAccessors.setTokens(merged);

    originalRequest._retry = true;
    originalRequest.headers.Authorization = `Bearer ${merged.access}`;
    return api(originalRequest);
  }
);

export { api };
