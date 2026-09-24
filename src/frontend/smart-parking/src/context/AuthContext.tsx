import React, { createContext, useState, useEffect, ReactNode } from 'react';
import { api } from '../services/api';
import { storage } from '../services/storage';

export interface User {
  id: string;
  nome: string;
  email: string;
  placa_veiculo?: string;
  cargo?: string;
}

export interface AuthContextData {
  user: User | null;
  isAuthenticated: boolean;
  loading: boolean;
  signIn: (email: string, senha: string) => Promise<void>;
  signOut: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextData>({} as AuthContextData);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    async function loadStorageData() {
      try {
        const token = await storage.getAccessToken();
        if (token) {
          const response = await api.get('/auth/me');
          setUser(response.data);
        }
      } catch (error) {
        await storage.clearTokens();
      } finally {
        setLoading(false);
      }
    }

    loadStorageData();
  }, []);

  const signIn = async (email: string, senha: string) => {
    const response = await api.post('/auth/login', { email, senha });
    const { access_token, refresh_token, user: userData } = response.data;

    await storage.setAccessToken(access_token);
    await storage.setRefreshToken(refresh_token);
    setUser(userData);
  };

  const signOut = async () => {
    await storage.clearTokens();
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        loading,
        signIn,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
