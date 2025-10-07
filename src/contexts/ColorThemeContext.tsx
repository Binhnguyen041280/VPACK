'use client';
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

export type ColorTheme = 'purple' | 'pink';

interface ColorPalette {
  primary: string;
  secondary: string;
  gradient: string;
  brand500: string;
}

interface ColorThemeContextType {
  colorTheme: ColorTheme;
  toggleColorTheme: () => void;
  currentColors: ColorPalette;
}

const colorPalettes: Record<ColorTheme, ColorPalette> = {
  purple: {
    primary: '#4A25E1',
    secondary: '#7B5AFF', 
    gradient: 'linear-gradient(15.46deg, #4A25E1 26.3%, #7B5AFF 86.4%)',
    brand500: '#4A25E1'
  },
  pink: {
    primary: '#E1254A',
    secondary: '#FF5A7B',
    gradient: 'linear-gradient(15.46deg, #E1254A 26.3%, #FF5A7B 86.4%)',
    brand500: '#E1254A'
  }
};

const ColorThemeContext = createContext<ColorThemeContextType | undefined>(undefined);

interface ColorThemeProviderProps {
  children: ReactNode;
}

export function ColorThemeProvider({ children }: ColorThemeProviderProps) {
  const [colorTheme, setColorTheme] = useState<ColorTheme>('purple');

  // Load theme from localStorage on mount
  useEffect(() => {
    const savedTheme = localStorage.getItem('colorTheme') as ColorTheme;
    if (savedTheme && (savedTheme === 'purple' || savedTheme === 'pink')) {
      setColorTheme(savedTheme);
    }
  }, []);

  // Save theme to localStorage when it changes
  useEffect(() => {
    localStorage.setItem('colorTheme', colorTheme);
  }, [colorTheme]);

  const toggleColorTheme = () => {
    setColorTheme(prev => prev === 'purple' ? 'pink' : 'purple');
  };

  const currentColors = colorPalettes[colorTheme];

  const value: ColorThemeContextType = {
    colorTheme,
    toggleColorTheme,
    currentColors
  };

  return (
    <ColorThemeContext.Provider value={value}>
      {children}
    </ColorThemeContext.Provider>
  );
}

export function useColorTheme() {
  const context = useContext(ColorThemeContext);
  if (context === undefined) {
    throw new Error('useColorTheme must be used within a ColorThemeProvider');
  }
  return context;
}

export default ColorThemeContext;