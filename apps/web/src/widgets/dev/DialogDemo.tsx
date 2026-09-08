"use client";

import { useState } from "react";
import { Button, Dialog } from "@lep/ui";

export function DialogDemo() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <Button onClick={() => setOpen(true)} variant="secondary">
        다이얼로그 열기
      </Button>
      <Dialog
        actions={
          <>
            <Button onClick={() => setOpen(false)} variant="secondary">
              취소
            </Button>
            <Button onClick={() => setOpen(false)} variant="primary">
              WBS에 반영
            </Button>
          </>
        }
        onClose={() => setOpen(false)}
        open={open}
        title="변경 반영 확인"
      >
        <p className="m-0">
          M3 마일스톤 기한을 09-19로 변경하면 후행 업무 2건의 기한도 함께 밀립니다.
        </p>
      </Dialog>
    </>
  );
}
