/**
 * Normalizes the backend base URL to ensure the API version prefix (/api/v1)
 * is consistently present regardless of whether NEXT_PUBLIC_API_URL is configured
 * with or without the /api/v1 suffix.
 */
export function getApiBaseUrl(): string {
  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!envUrl || !envUrl.trim()) {
    return "http://localhost:8000/api/v1";
  }
  const cleanUrl = envUrl.trim().replace(/\/+$/, "");
  if (cleanUrl.endsWith("/api/v1")) {
    return cleanUrl;
  }
  if (cleanUrl.endsWith("/api")) {
    return `${cleanUrl}/v1`;
  }
  return `${cleanUrl}/api/v1`;
}

/**
 * Normalizes an API endpoint to prevent missing or duplicated path prefixes.
 */
export function buildApiUrl(endpoint: string): string {
  const baseUrl = getApiBaseUrl();
  let cleanEndpoint = endpoint.trim();

  // Strip leading slash for prefix check
  if (cleanEndpoint.startsWith("/")) {
    cleanEndpoint = cleanEndpoint.substring(1);
  }

  // If caller accidentally passed /api/v1/... or api/v1/..., strip it to prevent /api/v1/api/v1/...
  if (cleanEndpoint.startsWith("api/v1/")) {
    cleanEndpoint = cleanEndpoint.substring("api/v1/".length);
  } else if (cleanEndpoint.startsWith("api/v1")) {
    cleanEndpoint = cleanEndpoint.substring("api/v1".length);
  } else if (cleanEndpoint.startsWith("api/")) {
    // If caller passed /api/... strip /api/
    cleanEndpoint = cleanEndpoint.substring("api/".length);
  }

  return `${baseUrl}/${cleanEndpoint.replace(/^\/+/, "")}`;
}

const API_BASE_URL = getApiBaseUrl();

interface RequestOptions extends RequestInit {
  token?: string;
}

export async function apiClient<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { token, headers = {}, ...customConfig } = options;

  let storedToken = token;
  if (!storedToken && typeof window !== "undefined") {
    storedToken = localStorage.getItem("hirelens_access_token") || undefined;
  }

  const defaultHeaders: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (storedToken) {
    defaultHeaders["Authorization"] = `Bearer ${storedToken}`;
  }

  const requestUrl = buildApiUrl(endpoint);

  const response = await fetch(requestUrl, {
    ...customConfig,
    headers: {
      ...defaultHeaders,
      ...headers,
    },
  });

  if (!response.ok) {
    let errorDetail = "An unexpected error occurred.";
    try {
      const errorJson = await response.json();
      errorDetail = errorJson.detail || errorDetail;
    } catch {
      if (response.status === 404) {
        errorDetail = "Requested resource or endpoint was not found (HTTP 404).";
      } else if (response.status === 429) {
        errorDetail = "Too many requests. Please wait a moment before trying again.";
      } else {
        errorDetail = `Request failed with status ${response.status}`;
      }
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

