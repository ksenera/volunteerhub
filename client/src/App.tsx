import { BrowserRouter as Router, Route, Routes } from "react-router-dom";
import "./App.css";
import ListingManager from "./components/listings/ListingManager";
import NavBar from "./components/navbar/navbar";
import RedeemPage from "./components/redeem/RedeemPage";

function App() {
  return (
    <Router>
      <NavBar />
      <Routes>
        <Route
          path="/"
          element={
            <main>
              <ListingManager />
            </main>
          }
        />
        <Route path="/redeem" element={<RedeemPage />} />
      </Routes>
    </Router>
  );
}

export default App;
