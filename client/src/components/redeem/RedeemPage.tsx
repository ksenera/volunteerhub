function RedeemPage() {
  const giftCards = [
    {
      src: "/assets/amazon.jpg",
      alt: "Amazon Gift Card",
      value: "3000",
    },
    {
      src: "/assets/starbucks.jpg",
      alt: "Starbucks Gift Card",
      value: "5000",
    },
    {
      src: "/assets/visa.jpeg",
      alt: "Visa Gift Card",
      value: "10000",
    },
  ];

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-gray-100 px-4">
      <h1 className="mb-8 text-4xl font-bold">Redeem Your Rewards</h1>

      <section className="flex flex-wrap justify-center gap-6" aria-label="Reward gift cards">
        {giftCards.map((card, index) => (
          <article
            key={index}
            className="flex flex-col items-center bg-white p-4 rounded-lg shadow-lg"
          >
            <img
              src={card.src}
              alt={card.alt}
              className="w-64 h-auto rounded-lg"
            />
            <button className="mt-4 px-6 py-2 bg-orange-500 text-white font-semibold rounded-lg hover:bg-orange-600">
              Redeem {card.value} points
            </button>
          </article>
        ))}
      </section>
    </main>
  );
}

export default RedeemPage;
