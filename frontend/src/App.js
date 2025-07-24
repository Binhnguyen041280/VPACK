import "@fontsource/montserrat";
import { useState } from "react";
import Dashboard from "./Dashboard";

function App() {
  const [activeMenu, setActiveMenu] = useState("Chương trình");
  return (
    <div className="flex min-h-screen bg-gray-900 text-white font-montserrat">
      <Dashboard setActiveMenu={setActiveMenu} activeMenu={activeMenu} />
    </div>
  );
}

export default App;