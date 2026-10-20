import { useContext } from "react";
import { AuthContext, type AuthContextData } from "../context/AuthContext";

export function useAuth(): AuthContextData {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth deve ser usado dentro de <AuthProvider>");
  }
  return ctx;
}
