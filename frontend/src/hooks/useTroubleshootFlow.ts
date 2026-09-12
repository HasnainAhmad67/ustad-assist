import { useCallback, useState } from 'react';
import { extractVision, getCatalog, troubleshoot } from '../services/api';
import type {
  CatalogResponse,
  TroubleshootRequest,
  TroubleshootResponse,
  VisionCandidateOut,
  VisionExtractResponse,
} from '../types/api';

export type FlowState =
  | 'idle'
  | 'identifying'
  | 'confirming'
  | 'retrieving'
  | 'result'
  | 'unsupported'
  | 'error';

export type FlowError = {
  message: string;
  context: 'catalog' | 'vision' | 'troubleshoot';
};

export function useTroubleshootFlow() {
  const [state, setState] = useState<FlowState>('idle');
  const [catalog, setCatalog] = useState<CatalogResponse | null>(null);
  const [vision, setVision] = useState<VisionExtractResponse | null>(null);
  const [candidates, setCandidates] = useState<VisionCandidateOut[]>([]);
  const [result, setResult] = useState<TroubleshootResponse | null>(null);
  const [error, setError] = useState<FlowError | null>(null);

  const loadCatalog = useCallback(async () => {
    if (catalog) return catalog;

    try {
      const data = await getCatalog();
      setCatalog(data);
      return data;
    } catch (cause) {
      const item: FlowError = {
        message:
          cause instanceof Error
            ? cause.message
            : 'Unable to load supported equipment.',
        context: 'catalog',
      };
      setError(item);
      setState('error');
      throw cause;
    }
  }, [catalog]);

  const beginManual = useCallback(async () => {
    setError(null);
    setVision(null);
    setCandidates([]);
    setResult(null);
    await loadCatalog();
    setState('identifying');
  }, [loadCatalog]);

  const beginImage = useCallback(() => {
    setError(null);
    setVision(null);
    setCandidates([]);
    setResult(null);
    setState('identifying');
  }, []);

  const submitImage = useCallback(async (file: File) => {
    setError(null);
    setVision(null);
    setCandidates([]);
    setResult(null);
    setState('identifying');

    try {
      const data = await extractVision(file);
      setVision(data);

      if (data.status === 'candidates_found') {
        setCandidates(data.candidates);
        setState('confirming');
      } else if (
        data.status === 'image_unclear' ||
        data.status === 'no_candidates'
      ) {
        setState('unsupported');
      } else {
        // The only remaining vision status is the exact backend value "error".
        setError({ message: data.message, context: 'vision' });
        setState('error');
      }

      return data;
    } catch (cause) {
      setError({
        message:
          cause instanceof Error ? cause.message : 'Image extraction failed.',
        context: 'vision',
      });
      setState('error');
      throw cause;
    }
  }, []);

  const submitTroubleshoot = useCallback(
    async (request: TroubleshootRequest) => {
      setError(null);
      setVision(null);
      setCandidates([]);
      setResult(null);
      setState('retrieving');

      try {
        const data = await troubleshoot(request);
        setResult(data);

        // The backend status is the sole source of truth for this branch.
        setState(
          data.status === 'equipment_not_supported' ? 'unsupported' : 'result',
        );
        return data;
      } catch (cause) {
        setError({
          message:
            cause instanceof Error
              ? cause.message
              : 'Troubleshooting request failed.',
          context: 'troubleshoot',
        });
        setState('error');
        throw cause;
      }
    },
    [],
  );

  const reset = useCallback(() => {
    setState('idle');
    setVision(null);
    setCandidates([]);
    setResult(null);
    setError(null);
  }, []);

  return {
    state,
    catalog,
    vision,
    candidates,
    result,
    error,
    loadCatalog,
    beginManual,
    beginImage,
    submitImage,
    submitTroubleshoot,
    setCandidates,
    reset,
    setState,
  };
}
