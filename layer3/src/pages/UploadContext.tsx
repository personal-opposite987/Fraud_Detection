import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import type { Summary } from "../api/client";

// Persists last upload result across tab switches via sessionStorage
const STORAGE_KEY = "last_upload_result";

type UploadResult = {
  stats: Summary;
  preview: Record<string, unknown>[];
  row_count: number;
};

type UploadContextType = {
  lastResult: UploadResult | null;
  setLastResult: (r: UploadResult) => void;
  clearResult: () => void;
  // Increments each time a new upload completes — consumers use this
  // as a useEffect dependency to re-fetch metrics automatically.
  uploadVersion: number;
};

const UploadContext = createContext<UploadContextType | null>(null);

function loadFromStorage(): UploadResult | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as UploadResult) : null;
  } catch {
    return null;
  }
}

export function UploadProvider({ children }: { children: ReactNode }) {
  const [lastResult, setLastResultState] = useState<UploadResult | null>(loadFromStorage);
  const [uploadVersion, setUploadVersion] = useState(0);

  const setLastResult = useCallback((r: UploadResult) => {
    setLastResultState(r);
    setUploadVersion((v) => v + 1);
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(r));
    } catch {
      // sessionStorage full — not fatal
    }
  }, []);

  const clearResult = useCallback(() => {
    setLastResultState(null);
    sessionStorage.removeItem(STORAGE_KEY);
  }, []);

  return (
    <UploadContext.Provider value={{ lastResult, setLastResult, clearResult, uploadVersion }}>
      {children}
    </UploadContext.Provider>
  );
}

export function useUpload() {
  const ctx = useContext(UploadContext);
  if (!ctx) throw new Error("useUpload must be used inside <UploadProvider>");
  return ctx;
}
