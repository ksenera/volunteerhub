import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  createListing,
  deleteListing,
  fetchListings,
  generateSummary,
  Listing,
  ListingInput,
  updateListing,
} from "./api";

const emptyListing: ListingInput = {
  title: "",
  organization: "",
  organizationTypes: "",
  volunteerTypes: "",
  commitment: "Flexible",
  location: "Remote",
  applicationDeadline: "",
  website: "",
  distanceMinutes: 0,
};

function ListingManager() {
  const [listings, setListings] = useState<Listing[]>([]);
  const [form, setForm] = useState<ListingInput>(emptyListing);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [location, setLocation] = useState("");
  const [commitment, setCommitment] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");

  const locations = useMemo(
    () => Array.from(new Set(listings.map((listing) => listing.location))).sort(),
    [listings],
  );

  const loadListings = async () => {
    setIsLoading(true);
    setError("");
    try {
      const data = await fetchListings({ search, location, commitment });
      setListings(data.listings);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load listings.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadListings();
  }, [search, location, commitment]);

  const updateField = (field: keyof ListingInput, value: string) => {
    setForm((current) => ({
      ...current,
      [field]: field === "distanceMinutes" ? Number(value) : value,
    }));
  };

  const resetForm = () => {
    setForm(emptyListing);
    setEditingId(null);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSaving(true);
    setError("");
    try {
      if (editingId) {
        await updateListing(editingId, form);
      } else {
        await createListing(form);
      }
      resetForm();
      await loadListings();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the listing.");
    } finally {
      setIsSaving(false);
    }
  };

  const startEditing = (listing: Listing) => {
    setEditingId(listing.id);
    setForm({
      title: listing.title,
      organization: listing.organization,
      organizationTypes: listing.organizationTypes,
      volunteerTypes: listing.volunteerTypes,
      commitment: listing.commitment,
      location: listing.location,
      applicationDeadline: listing.applicationDeadline,
      website: listing.website,
      distanceMinutes: listing.distanceMinutes,
    });
  };

  const removeListing = async (id: number) => {
    setError("");
    try {
      await deleteListing(id);
      await loadListings();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete the listing.");
    }
  };

  const summarize = async (id: number) => {
    setError("");
    try {
      const updated = await generateSummary(id);
      setListings((current) =>
        current.map((listing) => (listing.id === id ? updated : listing)),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not generate a summary.");
    }
  };

  return (
    <section className="mx-auto max-w-6xl px-4 py-8" aria-labelledby="listings-title">
      <div className="mb-6 flex flex-col gap-2">
        <p className="text-sm font-semibold uppercase tracking-wide text-orange-600">
          VolunteerHub
        </p>
        <h1 id="listings-title" className="text-3xl font-bold text-slate-950">
          Volunteer Listings
        </h1>
        <p className="max-w-3xl text-slate-600">
          Create, edit, search, and filter volunteer opportunities saved through
          the Flask API.
        </p>
      </div>

      {error && (
        <div role="alert" className="mb-4 rounded border border-red-300 bg-red-50 p-3 text-red-800">
          {error}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
        <form
          onSubmit={handleSubmit}
          className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
          aria-label={editingId ? "Edit volunteer listing" : "Create volunteer listing"}
        >
          <h2 className="mb-4 text-xl font-semibold text-slate-950">
            {editingId ? "Edit Listing" : "New Listing"}
          </h2>

          <label className="mb-3 block text-sm font-medium text-slate-700">
            Title
            <input
              required
              value={form.title}
              onChange={(event) => updateField("title", event.target.value)}
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            />
          </label>

          <label className="mb-3 block text-sm font-medium text-slate-700">
            Organization
            <input
              required
              value={form.organization}
              onChange={(event) => updateField("organization", event.target.value)}
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            />
          </label>

          <label className="mb-3 block text-sm font-medium text-slate-700">
            Organization types
            <input
              value={form.organizationTypes}
              onChange={(event) => updateField("organizationTypes", event.target.value)}
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            />
          </label>

          <label className="mb-3 block text-sm font-medium text-slate-700">
            Volunteer types
            <input
              value={form.volunteerTypes}
              onChange={(event) => updateField("volunteerTypes", event.target.value)}
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            />
          </label>

          <label className="mb-3 block text-sm font-medium text-slate-700">
            Commitment
            <select
              value={form.commitment}
              onChange={(event) => updateField("commitment", event.target.value)}
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            >
              <option>Flexible</option>
              <option>Short term</option>
              <option>Long term</option>
              <option>Ongoing</option>
            </select>
          </label>

          <label className="mb-3 block text-sm font-medium text-slate-700">
            Location
            <input
              required
              value={form.location}
              onChange={(event) => updateField("location", event.target.value)}
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            />
          </label>

          <label className="mb-3 block text-sm font-medium text-slate-700">
            Deadline
            <input
              value={form.applicationDeadline}
              onChange={(event) => updateField("applicationDeadline", event.target.value)}
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            />
          </label>

          <label className="mb-3 block text-sm font-medium text-slate-700">
            Website
            <input
              type="url"
              value={form.website}
              onChange={(event) => updateField("website", event.target.value)}
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            />
          </label>

          <label className="mb-4 block text-sm font-medium text-slate-700">
            Travel time in minutes
            <input
              min="0"
              type="number"
              value={form.distanceMinutes}
              onChange={(event) => updateField("distanceMinutes", event.target.value)}
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            />
          </label>

          <div className="flex gap-2">
            <button
              type="submit"
              disabled={isSaving}
              className="rounded bg-orange-600 px-4 py-2 font-semibold text-white hover:bg-orange-700 disabled:opacity-60"
            >
              {isSaving ? "Saving..." : editingId ? "Save Changes" : "Create Listing"}
            </button>
            {editingId && (
              <button
                type="button"
                onClick={resetForm}
                className="rounded border border-slate-300 px-4 py-2 font-semibold text-slate-800"
              >
                Cancel
              </button>
            )}
          </div>
        </form>

        <div>
          <div className="mb-4 grid gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm md:grid-cols-3">
            <label className="text-sm font-medium text-slate-700">
              Search
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Title, organization, type"
                className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
              />
            </label>

            <label className="text-sm font-medium text-slate-700">
              Location
              <select
                value={location}
                onChange={(event) => setLocation(event.target.value)}
                className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
              >
                <option value="">All locations</option>
                {locations.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>

            <label className="text-sm font-medium text-slate-700">
              Commitment
              <select
                value={commitment}
                onChange={(event) => setCommitment(event.target.value)}
                className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
              >
                <option value="">All commitments</option>
                <option>Flexible</option>
                <option>Short term</option>
                <option>Long term</option>
                <option>Ongoing</option>
              </select>
            </label>
          </div>

          {isLoading ? (
            <p role="status" className="rounded-lg border border-slate-200 p-6 text-slate-600">
              Loading listings...
            </p>
          ) : listings.length === 0 ? (
            <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center">
              <h2 className="text-xl font-semibold text-slate-950">No listings found</h2>
              <p className="mt-2 text-slate-600">
                Add a listing or clear the current search and filters.
              </p>
            </div>
          ) : (
            <div className="grid gap-4">
              {listings.map((listing) => (
                <article
                  key={listing.id}
                  className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
                >
                  <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                    <div>
                      <h2 className="text-xl font-semibold text-slate-950">{listing.title}</h2>
                      <p className="font-medium text-slate-700">{listing.organization}</p>
                      <p className="mt-2 text-sm text-slate-600">
                        {listing.commitment} | {listing.location} |{" "}
                        {listing.distanceMinutes} min
                      </p>
                      <p className="mt-2 text-sm text-slate-600">
                        {listing.volunteerTypes || "No volunteer type listed"}
                      </p>
                      {listing.summary && (
                        <p className="mt-3 rounded border border-orange-200 bg-orange-50 p-3 text-sm text-slate-800">
                          {listing.summary}
                          <span className="mt-1 block text-xs text-slate-500">
                            {listing.summaryPromptVersion} |{" "}
                            {listing.summaryReviewStatus}
                          </span>
                        </p>
                      )}
                    </div>

                    <div className="flex flex-wrap gap-2">
                      {listing.website && (
                        <a
                          href={listing.website}
                          target="_blank"
                          rel="noreferrer"
                          className="rounded border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-800"
                        >
                          Website
                        </a>
                      )}
                      <button
                        type="button"
                        onClick={() => summarize(listing.id)}
                        className="rounded border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-800"
                      >
                        Generate Summary
                      </button>
                      <button
                        type="button"
                        onClick={() => startEditing(listing)}
                        className="rounded border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-800"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => removeListing(listing.id)}
                        className="rounded bg-slate-900 px-3 py-2 text-sm font-semibold text-white"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

export default ListingManager;
