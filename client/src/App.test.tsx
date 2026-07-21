import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { beforeEach, describe, expect, test, vi } from "vitest";
import App from "./App";
import type { Listing } from "./components/listings/api";

vi.mock("firebase/auth", () => ({
  getAuth: () => ({}),
  GoogleAuthProvider: vi.fn(),
  onAuthStateChanged: (_auth: unknown, callback: (user: null) => void) => {
    callback(null);
    return vi.fn();
  },
  signInWithPopup: vi.fn(),
  signOut: vi.fn(),
}));

vi.mock("firebase/app", () => ({
  getApps: () => [{}],
  initializeApp: vi.fn(),
}));

const baseListings: Listing[] = [
  {
    id: 1,
    title: "Community Event Organizer",
    organization: "Local Initiatives",
    organizationTypes: "Community",
    volunteerTypes: "Events",
    commitment: "Flexible",
    location: "Remote",
    applicationDeadline: "June 1, 2026",
    website: "https://example.org",
    distanceMinutes: 0,
    pointsValue: 50,
    claimed: false,
    summary: null,
    summaryPromptVersion: null,
    summaryReviewStatus: "not_generated",
  },
  {
    id: 2,
    title: "Food Bank Helper",
    organization: "Ottawa Food Bank",
    organizationTypes: "Community Support",
    volunteerTypes: "Food Security",
    commitment: "Ongoing",
    location: "Ottawa",
    applicationDeadline: "July 15, 2026",
    website: "https://food.example.org",
    distanceMinutes: 15,
    pointsValue: 500,
    claimed: false,
    summary: null,
    summaryPromptVersion: null,
    summaryReviewStatus: "not_generated",
  },
];

function installApiMock(options: { failListings?: boolean; pointsBalance?: number } = {}) {
  let listings: Listing[] = structuredClone(baseListings);
  let pointsBalance = options.pointsBalance ?? 0;

  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, request?: RequestInit) => {
      const endpoint = new URL(url);
      const method = request?.method ?? "GET";

      if (options.failListings && endpoint.pathname === "/api/listings") {
        return Response.json({ error: "Backend unavailable." }, { status: 500 });
      }

      if (endpoint.pathname === "/api/rewards" && method === "GET") {
        return Response.json({
          pointsBalance,
          rewards: [
            {
              id: "amazon",
              name: "Amazon Gift Card",
              pointsCost: 3000,
              canRedeem: pointsBalance >= 3000,
            },
            {
              id: "starbucks",
              name: "Starbucks Gift Card",
              pointsCost: 1000,
              canRedeem: pointsBalance >= 1000,
            },
          ],
        });
      }

      if (endpoint.pathname === "/api/rewards/redeem" && method === "POST") {
        pointsBalance -= 3000;
        return Response.json({
          pointsBalance,
          redeemedReward: {
            id: "amazon",
            name: "Amazon Gift Card",
            pointsCost: 3000,
            canRedeem: true,
          },
          rewards: [
            {
              id: "amazon",
              name: "Amazon Gift Card",
              pointsCost: 3000,
              canRedeem: pointsBalance >= 3000,
            },
          ],
        });
      }

      const claimMatch = endpoint.pathname.match(/^\/api\/listings\/(\d+)\/claim$/);
      if (claimMatch && method === "POST") {
        const id = Number(claimMatch[1]);
        const listing = listings.find((item) => item.id === id);
        if (!listing) return Response.json({ error: "Listing not found." }, { status: 404 });
        pointsBalance += listing.claimed ? 0 : listing.pointsValue;
        const updated = { ...listing, claimed: true };
        listings = listings.map((item) => (item.id === id ? updated : item));
        return Response.json({
          listing: updated,
          pointsBalance,
          awardedPoints: listing.claimed ? 0 : listing.pointsValue,
          alreadyClaimed: listing.claimed,
        });
      }

      const summaryMatch = endpoint.pathname.match(/^\/api\/listings\/(\d+)\/summary$/);
      if (summaryMatch && method === "POST") {
        const id = Number(summaryMatch[1]);
        const updated = {
          ...listings.find((item) => item.id === id)!,
          summary:
            "Community Event Organizer with Local Initiatives is a flexible volunteer opportunity in Remote.",
          summaryPromptVersion: "listing-summary-v1",
          summaryReviewStatus: "needs_review",
        };
        listings = listings.map((item) => (item.id === id ? updated : item));
        return Response.json(updated);
      }

      const listingMatch = endpoint.pathname.match(/^\/api\/listings\/(\d+)$/);
      if (listingMatch && method === "PUT") {
        const id = Number(listingMatch[1]);
        const body = JSON.parse(String(request?.body));
        const updated = {
          ...listings.find((item) => item.id === id)!,
          ...body,
          pointsValue: listings.find((item) => item.id === id)!.pointsValue,
          claimed: listings.find((item) => item.id === id)!.claimed,
        };
        listings = listings.map((item) => (item.id === id ? updated : item));
        return Response.json(updated);
      }

      if (listingMatch && method === "DELETE") {
        const id = Number(listingMatch[1]);
        listings = listings.filter((item) => item.id !== id);
        return new Response(null, { status: 204 });
      }

      if (endpoint.pathname === "/api/listings" && method === "POST") {
        const body = JSON.parse(String(request?.body));
        const created = {
          ...body,
          id: 3,
          pointsValue: 50,
          claimed: false,
          summary: null,
          summaryPromptVersion: null,
          summaryReviewStatus: "not_generated",
        };
        listings = [created, ...listings];
        return Response.json(created, { status: 201 });
      }

      if (endpoint.pathname === "/api/listings" && method === "GET") {
        const search = endpoint.searchParams.get("search")?.toLowerCase() ?? "";
        const location = endpoint.searchParams.get("location") ?? "";
        const commitment = endpoint.searchParams.get("commitment") ?? "";
        const filtered = listings.filter((listing) => {
          const searchable = [
            listing.title,
            listing.organization,
            listing.organizationTypes,
            listing.volunteerTypes,
          ]
            .join(" ")
            .toLowerCase();
          return (
            (!search || searchable.includes(search)) &&
            (!location || listing.location === location) &&
            (!commitment || listing.commitment === commitment)
          );
        });
        return Response.json({ listings: filtered });
      }

      return Response.json({ error: "Unhandled request." }, { status: 500 });
    }),
  );
}

describe("App", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.history.pushState({}, "", "/");
    installApiMock();
  });

  test("renders listings from the backend", async () => {
    render(<App />);

    expect(screen.getByRole("status")).toHaveTextContent("Loading listings");
    expect(await screen.findByText("Community Event Organizer")).toBeInTheDocument();
    expect(screen.getByText("Food Bank Helper")).toBeInTheDocument();
    expect(screen.getByText("50 points available")).toBeInTheDocument();
  });

  test("has no obvious accessibility violations on the listings screen", async () => {
    const { container } = render(<App />);

    await screen.findByText("Community Event Organizer");
    const results = await axe(container);

    expect(results.violations).toEqual([]);
  });

  test("searches and filters listings", async () => {
    const user = userEvent.setup();
    render(<App />);

    await screen.findByText("Community Event Organizer");
    await user.type(screen.getByLabelText(/^Search$/), "food");

    await waitFor(() => {
      expect(screen.queryByText("Community Event Organizer")).not.toBeInTheDocument();
    });
    expect(screen.getByText("Food Bank Helper")).toBeInTheDocument();

    await user.selectOptions(screen.getAllByLabelText(/^Location$/)[1], "Ottawa");
    expect(await screen.findByText("Food Bank Helper")).toBeInTheDocument();
  });

  test("creates, edits, and deletes a listing through the form", async () => {
    const user = userEvent.setup();
    render(<App />);

    await screen.findByText("Community Event Organizer");
    const form = screen.getByRole("form", { name: /create volunteer listing/i });
    await user.type(within(form).getByLabelText(/^Title$/), "Park Cleanup");
    await user.type(within(form).getByLabelText(/^Organization$/), "Green Ottawa");
    await user.clear(within(form).getByLabelText(/^Location$/));
    await user.type(within(form).getByLabelText(/^Location$/), "Ottawa");
    await user.click(screen.getByRole("button", { name: /create listing/i }));

    expect(await screen.findByText("Park Cleanup")).toBeInTheDocument();

    const card = screen.getByText("Park Cleanup").closest("article")!;
    await user.click(within(card).getByRole("button", { name: /^edit$/i }));
    await user.clear(within(form).getByLabelText(/^Title$/));
    await user.type(within(form).getByLabelText(/^Title$/), "Park Cleanup Lead");
    await user.click(screen.getByRole("button", { name: /save changes/i }));

    expect(await screen.findByText("Park Cleanup Lead")).toBeInTheDocument();

    const updatedCard = screen.getByText("Park Cleanup Lead").closest("article")!;
    await user.click(within(updatedCard).getByRole("button", { name: /^delete$/i }));

    await waitFor(() => {
      expect(screen.queryByText("Park Cleanup Lead")).not.toBeInTheDocument();
    });
  });

  test("generates a reviewable AI summary", async () => {
    const user = userEvent.setup();
    render(<App />);

    const card = (await screen.findByText("Community Event Organizer")).closest("article")!;
    await user.click(within(card).getByRole("button", { name: /generate summary/i }));

    expect(
      await screen.findByText(/Community Event Organizer with Local Initiatives/),
    ).toBeInTheDocument();
    expect(screen.getByText("listing-summary-v1 | needs_review")).toBeInTheDocument();
  });

  test("claims listing points", async () => {
    const user = userEvent.setup();
    render(<App />);

    const card = (await screen.findByText("Community Event Organizer")).closest("article")!;
    await user.click(within(card).getByRole("button", { name: /claim points/i }));

    expect(await screen.findByText("Claimed 50 points.")).toBeInTheDocument();
    expect(screen.getByText("Reward balance: 50 points")).toBeInTheDocument();
  });

  test("redeems a reward from the rewards page", async () => {
    installApiMock({ pointsBalance: 3500 });
    const user = userEvent.setup();
    window.history.pushState({}, "", "/redeem");

    render(<App />);

    expect(await screen.findByText("Current balance: 3500 points")).toBeInTheDocument();
    await user.click(screen.getAllByRole("button", { name: /redeem reward/i })[0]);

    expect(await screen.findByText("Redeemed Amazon Gift Card.")).toBeInTheDocument();
    expect(screen.getByText("Current balance: 500 points")).toBeInTheDocument();
  });

  test("shows an API error state", async () => {
    installApiMock({ failListings: true });
    render(<App />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Backend unavailable.");
  });
});
