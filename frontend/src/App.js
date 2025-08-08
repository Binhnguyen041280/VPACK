import "@fontsource/montserrat";
import { useState } from "react";
import Dashboard from "./Dashboard";
import GoogleSignupScreen from "./components/auth/GoogleSignupScreen";
import useAuthState from "./hooks/useAuthState";

function App() {
  const [activeMenu, setActiveMenu] = useState("Chương trình");
  const { authState, handleAuthSuccess, handleLogout } = useAuthState();

  // Show loading screen while checking authentication
  if (authState.isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
          <p className="text-white">Đang khởi tạo V_Track...</p>
        </div>
      </div>
    );
  }

  // Show Google signup screen on first run or if not authenticated
  if (authState.isFirstRun || !authState.isAuthenticated) {
    return (
      <GoogleSignupScreen 
        onAuthSuccess={handleAuthSuccess}
      />
    );
  }

  // Show main dashboard after authentication
  return (
    <div className="flex min-h-screen bg-gray-900 text-white font-montserrat">
      <Dashboard 
        setActiveMenu={setActiveMenu} 
        activeMenu={activeMenu}
        authState={authState}
        onLogout={handleLogout}
      />
    </div>
  );
}

export default App;