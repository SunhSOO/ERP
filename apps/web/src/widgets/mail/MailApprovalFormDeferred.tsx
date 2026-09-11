"use client";

import { Fragment, Suspense, use } from "react";
import type { MailMessage } from "@lep/api-client";
import type { MailProjectsResult } from "./mail-deferred-results";
import { MailApprovalForm } from "./MailApprovalForm";

interface MailApprovalFormDeferredProps {
  message: MailMessage;
  projectsPromise: Promise<MailProjectsResult>;
  reviewProjectId: string;
}

function MailApprovalFormContent({
  message,
  projectsPromise,
  reviewProjectId,
}: MailApprovalFormDeferredProps) {
  const result = use(projectsPromise);

  if (!result.ok) {
    return (
      <section className="flex flex-col gap-3 border border-divider p-3">
        <p className="text-danger m-0 text-[13px]">승인 프로젝트를 불러올 수 없습니다.</p>
      </section>
    );
  }

  return (
    <Fragment key={`${message.id}:${message.version}`}>
      <MailApprovalForm message={message} projects={result.projects} reviewProjectId={reviewProjectId} />
    </Fragment>
  );
}

export function MailApprovalFormDeferred({
  message,
  projectsPromise,
  reviewProjectId,
}: MailApprovalFormDeferredProps) {
  return (
    <Suspense fallback={<div className="text-muted text-[12px]">승인 프로젝트 불러오는 중…</div>}>
      <MailApprovalFormContent message={message} projectsPromise={projectsPromise} reviewProjectId={reviewProjectId} />
    </Suspense>
  );
}
