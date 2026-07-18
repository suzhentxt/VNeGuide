"use client";

import { useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { toast } from "sonner";

const NOTICES: Record<string, string> = {
  chua_chon_dich_vu:
    "Vui lòng chọn dịch vụ và cơ quan tiếp nhận trước khi vào tờ khai.",
};

export function RedirectNotice() {
  const searchParams = useSearchParams();
  const code = searchParams.get("canh_bao");

  useEffect(() => {
    if (code && NOTICES[code]) toast.warning(NOTICES[code]);
  }, [code]);

  return null;
}
