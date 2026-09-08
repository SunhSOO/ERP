"use client";

import { useEffect, useRef } from "react";
import type { ReactNode } from "react";

export interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  /** 하단 버튼들. 확인 액션을 오른쪽 끝에 둔다. */
  actions?: ReactNode;
}

/** 네이티브 dialog 기반 모달.
 *
 * `showModal()`이 포커스 트랩, 배경 비활성화, ESC 닫기를 전부 브라우저에서
 * 제공한다. 직접 구현하면 놓치기 쉬운 부분이라 플랫폼에 맡긴다.
 * 06_UI_UX 13절의 모달 요구사항이 이것으로 충족된다. */
export function Dialog({ open, onClose, title, children, actions }: DialogProps) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    if (open && !element.open) {
      element.showModal();
    } else if (!open && element.open) {
      element.close();
    }
  }, [open]);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    // ESC와 배경 클릭 모두 브라우저가 close 이벤트로 알려준다.
    const handleClose = () => onClose();
    element.addEventListener("close", handleClose);
    return () => element.removeEventListener("close", handleClose);
  }, [onClose]);

  return (
    <dialog ref={ref} className="dialog" aria-labelledby="dialog-title">
      <h2 className="dialog-title" id="dialog-title">
        {title}
      </h2>
      <div className="dialog-body">{children}</div>
      {actions ? <div className="dialog-actions">{actions}</div> : null}
    </dialog>
  );
}
