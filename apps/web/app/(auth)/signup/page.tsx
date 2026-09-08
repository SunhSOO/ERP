import Link from "next/link";
import { redirect } from "next/navigation";
import { InputField } from "@lep/ui";
import { gateway } from "@/src/shared/data/gateway";
import { signupAction } from "@/src/shared/data/actions";
import { AuthForm } from "@/src/widgets/auth/AuthForm";

export const dynamic = "force-dynamic";

export default async function SignupPage() {
  if (await gateway.me()) redirect("/home");

  const { first_account } = await gateway.signupState();

  return (
    <>
      <div className="flex flex-col gap-1">
        <h1 className="m-0 text-[20px]">가입</h1>
        <p className="text-muted m-0 text-[13px]">
          {first_account
            ? "이 서버의 첫 계정입니다. 관리자 권한을 받습니다."
            : "필요한 정보를 입력하세요."}
        </p>
      </div>

      <AuthForm action={signupAction} submitLabel="가입하고 시작하기">
        <InputField
          autoComplete="email"
          label="이메일"
          name="email"
          required
          type="email"
        />
        <InputField
          autoComplete="name"
          label="이름"
          name="display_name"
          required
          type="text"
        />
        <InputField
          autoComplete="new-password"
          hint="10자 이상"
          label="비밀번호"
          minLength={10}
          name="password"
          required
          type="password"
        />
      </AuthForm>

      <p className="text-muted m-0 text-[12.5px]">
        이미 계정이 있나요? <Link href="/login">로그인</Link>
      </p>
    </>
  );
}
