"use client";

import Link from "next/link";
import { Suspense, use } from "react";
import type { MailProjectsResult } from "./mail-deferred-results";

interface MailProjectsNavProps {
  projectsPromise: Promise<MailProjectsResult>;
  status: "unclassified" | "project" | "unrelated" | "all";
  projectId: string;
}

function MailProjectsNavContent({ projectsPromise, status, projectId }: MailProjectsNavProps) {
  const result = use(projectsPromise);

  function projectHref(projId: string): string {
    return `/projects/${encodeURIComponent(projId)}/mail?${new URLSearchParams({
      status: "project",
      page: "1",
    }).toString()}`;
  }

  if (!result.ok) {
    return <li className="text-danger text-[12px]">프로젝트를 불러올 수 없습니다.</li>;
  }

  if (result.projects.length === 0) {
    return <li className="text-muted text-[12px]">등록된 프로젝트가 없습니다.</li>;
  }

  return (
    <>
      {result.projects.map((project) => (
        <li key={project.id}>
          <Link
            aria-current={status === "project" && project.id === projectId ? "page" : undefined}
            className="rounded border border-divider px-2 py-1 text-[12px] no-underline hover:border-accent hover:text-accent"
            href={projectHref(project.id)}
          >
            {project.name}
          </Link>
        </li>
      ))}
    </>
  );
}

export function MailProjectsNav({ projectsPromise, status, projectId }: MailProjectsNavProps) {
  return (
    <Suspense
      fallback={<li className="text-muted text-[12px]">프로젝트 불러오는 중…</li>}
    >
      <MailProjectsNavContent projectsPromise={projectsPromise} status={status} projectId={projectId} />
    </Suspense>
  );
}
