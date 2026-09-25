import { useCallback, useEffect, useState } from "react";
import { loadArtifacts } from "../data/loadArtifacts";
import { PipelineArtifacts } from "../data/schemas";

type PipelineDataState = {
  artifacts: PipelineArtifacts | null;
  loading: boolean;
  lastReloadAt: Date | null;
  reload: () => Promise<void>;
};

export function usePipelineData(): PipelineDataState {
  const [artifacts, setArtifacts] = useState<PipelineArtifacts | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastReloadAt, setLastReloadAt] = useState<Date | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const loaded = await loadArtifacts();
      setArtifacts(loaded);
      setLastReloadAt(new Date());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { artifacts, loading, lastReloadAt, reload };
}
