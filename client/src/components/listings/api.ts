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
  pointsValue: number;
  claimed: boolean;
  summary?: string | null;
  summaryPromptVersion?: string | null;
  summaryReviewStatus?: string;
};

export type ListingInput = Omit<
  Listing,
  | "id"
  | "pointsValue"
  | "claimed"
  | "summary"
  | "summaryPromptVersion"
  | "summaryReviewStatus"
>;

export type Reward = {
  id: string;
  name: string;
  pointsCost: number;
  canRedeem: boolean;
};

export type RewardsState = {
  pointsBalance: number;
  rewards: Reward[];
};

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

export function claimListing(id: number) {
  return request<{
    listing: Listing;
    pointsBalance: number;
    awardedPoints: number;
    alreadyClaimed: boolean;
  }>(`/api/listings/${id}/claim`, {
    method: "POST",
  });
}

export function fetchRewards() {
  return request<RewardsState>("/api/rewards");
}

export function redeemReward(rewardId: string) {
  return request<RewardsState & { redeemedReward: Reward }>("/api/rewards/redeem", {
    method: "POST",
    body: JSON.stringify({ rewardId }),
  });
}
