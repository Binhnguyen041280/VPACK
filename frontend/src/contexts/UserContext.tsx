'use client';
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface UserInfo {
  name: string;
  avatar: string;
  email: string;
  authenticated: boolean;
}

interface UserContextType {
  userInfo: UserInfo;
  updateUserInfo: (info: Partial<UserInfo>) => void;
  refreshUserInfo: () => Promise<void>;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

export const useUser = () => {
  const context = useContext(UserContext);
  if (context === undefined) {
    throw new Error('useUser must be used within a UserProvider');
  }
  return context;
};

interface UserProviderProps {
  children: ReactNode;
}

export const UserProvider: React.FC<UserProviderProps> = ({ children }) => {
  console.log('🚀 UserProvider component mounted');
  
  const [userInfo, setUserInfo] = useState<UserInfo>({
    name: 'Guest',
    avatar: '/img/avatars/avatar4.png',
    email: '',
    authenticated: false
  });

  const updateUserInfo = (info: Partial<UserInfo>) => {
    console.log('🔄 updateUserInfo called with:', info);
    console.log('🔄 Previous userInfo:', userInfo);
    setUserInfo(prev => {
      const newUserInfo = { ...prev, ...info };
      console.log('🔄 New userInfo will be:', newUserInfo);
      return newUserInfo;
    });
  };

  const refreshUserInfo = async () => {
    try {
      console.log('🔍 STARTING user info fetch...');
      
          // Simple direct database call
      console.log('🔄 Getting user data from database...');
      const dbResponse = await fetch('http://localhost:8080/api/user/latest', {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      console.log('📡 API Response status:', dbResponse.status);
      if (dbResponse.ok) {
        const dbData = await dbResponse.json();
        console.log('📊 API Data received:', dbData);
        
        if (dbData.success && dbData.user) {
          const userUpdate = {
            name: dbData.user.display_name || 'User',
            avatar: dbData.user.photo_url || '/img/avatars/avatar4.png',  
            email: dbData.user.gmail_address || '',
            authenticated: true // Mark as authenticated since we have real data
          };
          console.log('👤 UPDATING userInfo to:', userUpdate);
          setUserInfo(userUpdate); // Direct update instead of updateUserInfo
          console.log('✅ UserInfo updated successfully!');
        } else {
          console.log('❌ No user data in API response');
        }
      } else {
        console.log('❌ API call failed');
      }
      
    } catch (error) {
      console.log('❌ Could not fetch user info:', error);
    }
  };

  // Removed auto-fetch on mount for clean first-time experience
  // Users will have default state until explicit actions taken

  return (
    <UserContext.Provider value={{ userInfo, updateUserInfo, refreshUserInfo }}>
      {children}
    </UserContext.Provider>
  );
};