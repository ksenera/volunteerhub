import { useEffect, useState } from "react";
import amazonCard from "../../../assets/amazon.jpg";
import starbucksCard from "../../../assets/starbucks.jpg";
import visaCard from "../../../assets/visa.jpeg";
import { fetchRewards, redeemReward, Reward } from "../listings/api";

const rewardImages: Record<string, { src: string; alt: string }> = {
  amazon: { src: amazonCard, alt: "Amazon gift card" },
  starbucks: { src: starbucksCard, alt: "Starbucks gift card" },
  visa: { src: visaCard, alt: "Visa gift card" },
};

function RedeemPage() {
  const [pointsBalance, setPointsBalance] = useState(0);
  const [rewards, setRewards] = useState<Reward[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const loadRewards = async () => {
    setIsLoading(true);
    setError("");
    try {
      const data = await fetchRewards();
      setPointsBalance(data.pointsBalance);
      setRewards(data.rewards);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load rewards.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadRewards();
  }, []);

  const handleRedeem = async (reward: Reward) => {
    setError("");
    setMessage("");
    try {
      const data = await redeemReward(reward.id);
      setPointsBalance(data.pointsBalance);
      setRewards(data.rewards);
      setMessage(`Redeemed ${data.redeemedReward.name}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not redeem that reward.");
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-6xl flex-col px-4 py-10">
      <div className="mb-8">
        <p className="text-sm font-semibold uppercase tracking-wide text-orange-600">
          Rewards
        </p>
        <h1 className="text-4xl font-bold text-slate-950">Redeem Your Rewards</h1>
        <p className="mt-2 text-slate-600">
          Claim points from completed volunteer listings, then redeem them for
          prototype gift card rewards.
        </p>
        <p className="mt-4 w-fit rounded border border-orange-200 bg-orange-50 px-3 py-2 font-semibold text-orange-800">
          Current balance: {pointsBalance} points
        </p>
      </div>

      {error && (
        <div role="alert" className="mb-4 rounded border border-red-300 bg-red-50 p-3 text-red-800">
          {error}
        </div>
      )}
      {message && (
        <div role="status" className="mb-4 rounded border border-green-300 bg-green-50 p-3 text-green-800">
          {message}
        </div>
      )}

      {isLoading ? (
        <p role="status" className="rounded-lg border border-slate-200 p-6 text-slate-600">
          Loading rewards...
        </p>
      ) : (
        <section className="grid gap-6 md:grid-cols-3" aria-label="Reward gift cards">
          {rewards.map((reward) => {
            const image = rewardImages[reward.id];
            return (
              <article
                key={reward.id}
                className="flex flex-col rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
              >
                {image && (
                  <img
                    src={image.src}
                    alt={image.alt}
                    className="aspect-[16/10] w-full rounded object-cover"
                  />
                )}
                <div className="mt-4 flex flex-1 flex-col">
                  <h2 className="text-xl font-semibold text-slate-950">{reward.name}</h2>
                  <p className="mt-1 text-slate-600">{reward.pointsCost} points</p>
                  <button
                    type="button"
                    onClick={() => handleRedeem(reward)}
                    disabled={!reward.canRedeem}
                    className="mt-4 rounded bg-orange-600 px-4 py-2 font-semibold text-white hover:bg-orange-700 disabled:bg-slate-300 disabled:text-slate-600"
                  >
                    {reward.canRedeem ? "Redeem Reward" : "Not Enough Points"}
                  </button>
                </div>
              </article>
            );
          })}
        </section>
      )}
    </main>
  );
}

export default RedeemPage;
