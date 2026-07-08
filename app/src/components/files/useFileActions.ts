import { useLingui } from "@lingui/react/macro";
import { notifications } from "@mantine/notifications";
import { useState } from "react";
import { toRequestError } from "../../api/client";
import { filesApi } from "../../api/files";

/**
 * Returns a helper that requests a short-lived signed link for a file and opens
 * it in a new tab, plus the id currently being fetched (for button spinners).
 */
export function useOpenFile(expiresIn = 3600) {
  const { t } = useLingui();
  const [openingId, setOpeningId] = useState<string | null>(null);

  const openFile = async (fileId: string) => {
    setOpeningId(fileId);
    try {
      const { url } = await filesApi.link(fileId, { expiresIn });
      if (url) window.open(url, "_blank", "noopener");
    } catch (err) {
      notifications.show({
        color: "red",
        title: t`Could not open file`,
        message: toRequestError(err).message,
      });
    } finally {
      setOpeningId(null);
    }
  };

  return { openFile, openingId };
}
