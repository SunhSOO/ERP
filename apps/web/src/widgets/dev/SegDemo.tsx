"use client";

import { useState } from "react";
import { Seg } from "@lep/ui";

const OPTIONS = [
  { value: "vendor", label: "용역사" },
  { value: "client", label: "발주사" },
] as const;

export function SegDemo() {
  const [value, setValue] = useState<"vendor" | "client">("vendor");
  return <Seg legend="보기 역할" onChange={setValue} options={OPTIONS} value={value} />;
}
