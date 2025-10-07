'use client';
import { createContext, useContext, useState, ReactNode } from 'react';

interface RouteContextType {
  companyName: string;
  setCompanyName: (name: string) => void;
  isAnimating: boolean;
  startAnimation: () => void;
  stopAnimation: () => void;
  currentRoute: string;
  setCurrentRoute: (route: string) => void;
}

const RouteContext = createContext<RouteContextType | undefined>(undefined);

export const useRoute = () => {
  const context = useContext(RouteContext);
  if (context === undefined) {
    throw new Error('useRoute must be used within a RouteProvider');
  }
  return context;
};

interface RouteProviderProps {
  children: ReactNode;
}

export const RouteProvider: React.FC<RouteProviderProps> = ({ children }) => {
  const [companyName, setCompanyName] = useState<string>('Alan_go'); // Default for first-time users
  const [isAnimating, setIsAnimating] = useState<boolean>(false);
  const [currentRoute, setCurrentRoute] = useState<string>(''); // Track current active route

  const startAnimation = () => {
    setIsAnimating(true);
  };

  const stopAnimation = () => {
    setIsAnimating(false);
  };

  return (
    <RouteContext.Provider value={{ 
      companyName, 
      setCompanyName, 
      isAnimating, 
      startAnimation, 
      stopAnimation,
      currentRoute,
      setCurrentRoute
    }}>
      {children}
    </RouteContext.Provider>
  );
};