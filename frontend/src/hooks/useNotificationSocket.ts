import { useEffect } from 'react';
import { api } from '../services/api';
import { getStoredTokens } from '../services/api';

/**
 * Keeps the unread notification counter fresh.
 * Polls every 30s — simple and robust; the WebSocket in the chat page
 * handles the realtime path for messages.
 */
export function useNotificationSocket(setUnread: (n: number) => void): void {
  useEffect(() => {
    if (!getStoredTokens()) return;
    let cancelled = false;

    async function tick() {
      try {
        const resp = await api.get('/notifications/unread-count');
        if (!cancelled) setUnread(resp.data.count || 0);
      } catch {
        /* ignore transient errors */
      }
    }

    tick();
    const id = window.setInterval(tick, 30000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [setUnread]);
}
