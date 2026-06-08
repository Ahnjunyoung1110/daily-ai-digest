"use client";

// next-themes ThemeProvider 래퍼
// layout.tsx(서버 컴포넌트)에서 직접 next-themes import 불가 → 클라 컴포넌트로 분리
import { ThemeProvider as NextThemesProvider } from "next-themes";
import type { ThemeProviderProps } from "next-themes";

export function ThemeProvider({ children, ...props }: ThemeProviderProps) {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>;
}
