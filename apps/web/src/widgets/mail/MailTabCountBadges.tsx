"use client";

import { Suspense, use } from "react";
import type { MailCounts } from "@lep/api-client";

interface MailTabCountBadgesProps {
  countsPromise: Promise<MailCounts | null>;
  status: "unclassified" | "project" | "unrelated" | "all";
}

function MailTabCountBadgeContent({ countsPromise, status }: MailTabCountBadgesProps) {
  const counts = use(countsPromise);

  if (!counts) {
    return "";
  }

  return ` (${counts[status]})`;
}

export function MailTabCountBadge({ countsPromise, status }: MailTabCountBadgesProps) {
  return (
    <Suspense fallback="">
      <MailTabCountBadgeContent countsPromise={countsPromise} status={status} />
    </Suspense>
  );
}
