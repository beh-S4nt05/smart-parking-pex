import React, {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useState,
  ReactNode,
} from "react";
import { parkingApi } from "../services/api";
import { storage } from "../services/storage";
import type { Tokens, Usuario } from "../types/api";

export type { Usuario };

const ROLES_PAINEL = ["admin", "gestor", "financeiro"];

export interface AuthContextData {
  user: Usuario | null;
  isAuthenticated: boolean;
  /** admin, gestor ou financeiro — enxerga o painel/dashboard */
  canAccessPanel: boolean;
  isAdmin: boolean;
  loading: boolean;
  /** credencial = e-mail OU telefone (o backend aceita os dois) */
  signIn: (credencial: string, senha: string) => Promise<Usuario>;
  register: (payload: {
    nome: string;
    email: string;
    senha: string;
    telefone?: string;
    placa_veiculo?: string;
    /** RF-47 */ is_pcd?: boolean;
  }) => Promise<Usuario>;
  signOut: () => Promise<void>;
  /** rebusca /auth/me após edições do perfil (RF-15) */
  refreshUser: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextData | null>(null);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({
  children,
}) => {
  const [user, setUser] = useState<Usuario | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Boot: restaura sessão gravada. Mostra o cache imediatamente (app usável
  // offline) e revalida com /auth/me em seguida.
  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const token = await storage.getAccessToken();
        const cached = await storage.getUserCache();
        if (cached) {
          try {
            setUser(JSON.parse(cached));
          } catch {
            /* cache corrompido — segue */
          }
        }
        if (token) {
          try {
            const me = await parkingApi.me();
            if (!alive) return;
            setUser(me);
            await storage.setUserCache(JSON.stringify(me));
          } catch {
            if (!alive) return;
            // se o refresh automático do interceptor também falhou,
            // a sessão expirou de vez → limpa credenciais
            await storage.clearTokens();
            setUser(null);
          }
        }
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const signIn = useCallback(async (credencial: string, senha: string) => {
    const data: Tokens = await parkingApi.login(credencial, senha);
    const usuario =
      data.user ??
      (await parkingApi.me().catch(() => null));
    if (usuario) {
      setUser(usuario);
      await storage.setUserCache(JSON.stringify(usuario));
    }
    if (!usuario) throw new Error("Não foi possível carregar o perfil");
    return usuario;
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      const me = await parkingApi.me();
      setUser(me);
      await storage.setUserCache(JSON.stringify(me));
    } catch {
      /* offline mantém o cache — nada a fazer */
    }
  }, []);

  const register = useCallback(
    async (payload: {
      nome: string;
      email: string;
      senha: string;
      telefone?: string;
      placa_veiculo?: string;
      is_pcd?: boolean;
    }) => parkingApi.registrar(payload),
    [],
  );

  const signOut = useCallback(async () => {
    await parkingApi.logout();
    setUser(null);
  }, []);

  const value = useMemo<AuthContextData>(
    () => ({
      user,
      isAuthenticated: !!user,
      canAccessPanel: !!user && ROLES_PAINEL.includes(user.role),
      isAdmin: user?.role === "admin",
      loading,
      signIn,
      register,
      signOut,
      refreshUser,
    }),
    [user, loading, signIn, register, signOut, refreshUser],
  );

  return (
    <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
  );
};
