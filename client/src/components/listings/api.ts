export type Listing = {
  id: number;
  title: string;
  organization: string;
  organizationTypes: string;
  volunteerTypes: string;
  commitment: string;
  location: string;
  applicationDeadline: string;
  website: string;
  distanceMinutes: number;
  summary?: string | null;
  summaryPromptVersion?: string | null;
  summaryReviewStatus?: string;
};

export type ListingInput = Omit<
  Listing,
  "id" | "summary" | "summaryPromptVersion" | "summaryReviewStatus"
>;

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.error || "Request failed. Please try again.");
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

export async function fetchListings(filters: {
  search: string;
  location: string;
  commitment: string;
}) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  const query = params.toString();
  return request<{ listings: Listing[] }>(`/api/listings${query ? `?${query}` : ""}`);
}

export function createListing(listing: ListingInput) {
  return request<Listing>("/api/listings", {
    method: "POST",
    body: JSON.stringify(listing),
  });
}

export function updateListing(id: number, listing: ListingInput) {
  return request<Listing>(`/api/listings/${id}`, {
    method: "PUT",
    body: JSON.stringify(listing),
  });
}

export function deleteListing(id: number) {
  return request<void>(`/api/listings/${id}`, {
    method: "DELETE",
  });
}

export function generateSummary(id: number) {
  return request<Listing>(`/api/listings/${id}/summary`, {
    method: "POST",
  });
}
