"use client";

import { Suspense, use } from "react";
import type { MailCounts } from "@lep/api-client";

interface MailCountsHeaderProps {
  countsPromise: Promise<MailCounts | null>;
}

function MailCountsContent({ countsPromise }: MailCountsHeaderProps) {
  const counts = use(countsPromise);

  if (!counts) {
    return "건수를 확인할 수 없습니다";
  }

  return `미분류 ${counts.unclassified}건`;
}

export function MailCountsHeader({ countsPromise }: MailCountsHeaderProps) {
  return (
    <Suspense fallback="건수 불러오는 중…">
      <MailCountsContent countsPromise={countsPromise} />
    </Suspense>
  );
}
