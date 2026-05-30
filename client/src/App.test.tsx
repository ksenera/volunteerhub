import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";
import App from "./App";

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

const listings = [
  {
    id: 1,
    title: "Community Event Organizer",
    organization: "Local Initiatives",
    organizationTypes: "Community",
    volunteerTypes: "Events",
    commitment: "Flexible",
    location: "Remote",
    applicationDeadline: "June 1, 2025",
    website: "https://example.org",
    distanceMinutes: 0,
    pointsValue: 50,
    claimed: false,
    summary: null,
    summaryPromptVersion: null,
    summaryReviewStatus: "not_generated",
  },
];

describe("App", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.history.pushState({}, "", "/");
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, options?: RequestInit) => {
        if (url.includes("/api/rewards")) {
          return Response.json({
            pointsBalance: 0,
            rewards: [
              {
                id: "amazon",
                name: "Amazon Gift Card",
                pointsCost: 3000,
                canRedeem: false,
              },
            ],
          });
        }

        if (url.includes("/api/listings/1/claim")) {
          return Response.json({
            listing: { ...listings[0], claimed: true },
            pointsBalance: 50,
            awardedPoints: 50,
            alreadyClaimed: false,
          });
        }

        if (url.includes("/api/listings") && options?.method === "POST") {
          return Response.json({ ...listings[0], id: 2 }, { status: 201 });
        }

        return Response.json({ listings });
      }),
    );
  });

  test("renders listings from the backend", async () => {
    render(<App />);

    expect(screen.getByRole("status")).toHaveTextContent("Loading listings");
    expect(await screen.findByText("Community Event Organizer")).toBeInTheDocument();
    expect(screen.getByText("Local Initiatives")).toBeInTheDocument();
    expect(screen.getByText("50 points available")).toBeInTheDocument();
  });

  test("creates a listing through the form", async () => {
    const user = userEvent.setup();
    render(<App />);

    await screen.findByText("Community Event Organizer");
    const form = screen.getByRole("form", { name: /create volunteer listing/i });
    await user.type(within(form).getByLabelText(/^Title$/), "Food Bank Helper");
    await user.type(within(form).getByLabelText(/^Organization$/), "Ottawa Food Bank");
    await user.clear(within(form).getByLabelText(/^Location$/));
    await user.type(within(form).getByLabelText(/^Location$/), "Ottawa");
    await user.click(screen.getByRole("button", { name: /create listing/i }));

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/listings"),
        expect.objectContaining({ method: "POST" }),
      );
    });
  });

  test("claims points for a listing", async () => {
    const user = userEvent.setup();
    render(<App />);

    await screen.findByText("Community Event Organizer");
    await user.click(screen.getByRole("button", { name: /claim points/i }));

    expect(await screen.findByText("Claimed 50 points.")).toBeInTheDocument();
    expect(screen.getByText("Reward balance: 50 points")).toBeInTheDocument();
  });
});
