import { useCallback, useEffect, useRef, useState } from 'react';
import type { Snapshot, PatientAction } from '../types';
import { clinicApi } from '../services/api';
/** Own server synchronization and command feedback for the dashboard. */
export function useClinic() {
  const [data, setData] = useState<Snapshot | null>(null),
    [error, setError] = useState(''),
    [offline, setOffline] = useState(false),
    [busy, setBusy] = useState(false),
    [notice, setNotice] = useState(''),
    [updated, setUpdated] = useState<Date | null>(null);
  const pending = useRef(false);
  const refresh = useCallback(async (signal?: AbortSignal) => {
    try {
      const snapshot = await clinicApi.getState(signal);
      if (signal?.aborted) return;
      setData((previous) =>
        previous && previous.revision > snapshot.revision ? previous : snapshot,
      );
      setUpdated(new Date());
      setOffline(false);
    } catch {
      if (!signal?.aborted) setOffline(true);
    }
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    void refresh(controller.signal);
    const id = setInterval(() => void refresh(controller.signal), 3000);
    return () => {
      controller.abort();
      clearInterval(id);
    };
  }, [refresh]);
  const command: PatientAction = async (patient, action, fields = {}) => {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await clinicApi.sendCommand(patient, action, fields);
      setNotice('Update saved to the audit history.');
      await refresh();
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Unable to save.');
      await refresh();
    } finally {
      pending.current = false;
      setBusy(false);
    }
  };
  function clearFeedback() {
    setError('');
    setNotice('');
  }
  return { data, error, offline, busy, notice, updated, command, clearFeedback };
}
