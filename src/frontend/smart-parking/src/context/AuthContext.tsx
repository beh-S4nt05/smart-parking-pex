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
import { erroRevogaSessao, ROLES_PAINEL } from "../services/authFlow";
import type { Tokens, Usuario } from "../types/api";

export type { Usuario };

async function cachearUsuario(usuario: Usuario): Promise<void> {
  try {
    await storage.setUserCache(JSON.stringify(usuario));
  } catch (error) {
    // Cache acelera o boot, mas não é credencial: uma falha nele não pode
    // transformar um login já autenticado em erro nem apagar os tokens.
    console.warn("[smart-parking] Cache do usuário não foi atualizado", error);
  }
}

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
      let usuarioCacheado: Usuario | null = null;
      try {
        const token = await storage.getAccessToken();
        const cached = await storage.getUserCache();
        if (!token) {
          // Sem token NÃO existe sessão — o cache de usuário é lixo de
          // sessão anterior e nunca pode abrir guardas de rota sozinho.
          if (cached) await storage.clearUserCache().catch(() => undefined);
          return;
        }
        if (cached) {
          try {
            usuarioCacheado = JSON.parse(cached) as Usuario;
            setUser(usuarioCacheado);
          } catch {
            /* cache corrompido — a revalidação online decide */
          }
        }
        try {
          const me = await parkingApi.me();
          if (!alive) return;
          setUser(me);
          await cachearUsuario(me);
        } catch (error) {
          if (!alive) return;
          if (erroRevogaSessao(error)) {
            // 401/403 depois da tentativa de refresh: credencial inválida de
            // fato. Rede, timeout, 429 e 5xx NÃO destroem uma sessão válida.
            await storage.clearTokens().catch(() => undefined);
            setUser(null);
          } else if (usuarioCacheado) {
            setUser(usuarioCacheado);
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
    const usuario = data.user ?? (await parkingApi.me());
    setUser(usuario);
    await cachearUsuario(usuario);
    return usuario;
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      const me = await parkingApi.me();
      setUser(me);
      await cachearUsuario(me);
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
    try {
      await parkingApi.logout();
    } catch (error) {
      console.warn("[smart-parking] Não foi possível limpar toda a sessão local", error);
    } finally {
      setUser(null);
    }
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
