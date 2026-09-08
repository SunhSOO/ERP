import Link from "next/link";
import { redirect } from "next/navigation";
import { InputField } from "@lep/ui";
import { gateway } from "@/src/shared/data/gateway";
import { loginAction } from "@/src/shared/data/actions";
import { AuthForm } from "@/src/widgets/auth/AuthForm";

export const dynamic = "force-dynamic";

export default async function LoginPage() {
  // 이미 로그인한 사람에게 로그인 화면을 보여 주지 않는다.
  if (await gateway.me()) redirect("/home");

  // 아무도 가입하지 않은 서버라면 로그인할 계정 자체가 없다. 가입으로 보낸다.
  const { first_account } = await gateway.signupState();
  if (first_account) redirect("/signup");

  return (
    <>
      <div className="flex flex-col gap-1">
        <h1 className="m-0 text-[20px]">로그인</h1>
        <p className="text-muted m-0 text-[13px]">계정 정보를 입력하세요.</p>
      </div>

      <AuthForm action={loginAction} submitLabel="로그인">
        <InputField
          autoComplete="email"
          label="이메일"
          name="email"
          required
          type="email"
        />
        <InputField
          autoComplete="current-password"
          label="비밀번호"
          name="password"
          required
          type="password"
        />
      </AuthForm>

      <p className="text-muted m-0 text-[12.5px]">
        계정이 없나요? <Link href="/signup">가입하기</Link>
      </p>
    </>
  );
}
