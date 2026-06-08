/**
 * 관리자 로그인 POST 핸들러
 * 비번 일치 시 httpOnly 쿠키 발급 → /admin 리다이렉트
 */

import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const COOKIE_NAME = "admin_auth";
const COOKIE_MAX_AGE = 60 * 60 * 8; // 8시간

export async function POST(req: NextRequest) {
  const formData = await req.formData();
  const password = formData.get("password")?.toString() ?? "";

  const adminPassword = process.env.ADMIN_PASSWORD;
  if (!adminPassword) {
    return NextResponse.json(
      { error: "ADMIN_PASSWORD 환경변수가 설정되지 않았습니다." },
      { status: 500 }
    );
  }

  if (password !== adminPassword) {
    // 비번 불일치 — 로그인 페이지로 에러 파라미터와 함께 리다이렉트
    return NextResponse.redirect(new URL("/admin/login?error=1", req.url));
  }

  // 인증 성공 — httpOnly 쿠키 발급
  const cookieStore = await cookies();
  cookieStore.set(COOKIE_NAME, adminPassword, {
    httpOnly: true,
    sameSite: "lax",
    path: "/admin",
    maxAge: COOKIE_MAX_AGE,
    // 프로덕션에서는 secure: true 권장
    secure: process.env.NODE_ENV === "production",
  });

  return NextResponse.redirect(new URL("/admin", req.url));
}
