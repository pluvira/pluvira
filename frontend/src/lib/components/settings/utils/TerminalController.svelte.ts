import { api } from '$lib/api/client';

export class TerminalController {
  public isPolling = $state(false);
  private timer: ReturnType<typeof setInterval> | null = null;

  /**
   * Starts periodic polling for system execution logs.
   *
   * @param onLogs Callback triggered when new logs arrive.
   * @param intervalMs Polling interval in milliseconds (default 1000ms).
   */
  public startPolling(onLogs: (logs: string[]) => void, intervalMs = 1000): void {
    this.stopPolling();
    this.isPolling = true;
    this.fetchLogs(onLogs);
    this.timer = setInterval(() => {
      this.fetchLogs(onLogs);
    }, intervalMs);
  }

  /**
   * Fetches recent system logs from API client.
   *
   * @param onLogs Callback triggered with fetched logs array.
   */
  public async fetchLogs(onLogs: (logs: string[]) => void): Promise<void> {
    try {
      const logs = await api.getSystemLogs(200);
      if (logs && Array.isArray(logs)) {
        onLogs(logs);
      }
    } catch {
      // Ignore poll error
    }
  }

  /**
   * Stops active log polling timer.
   */
  public stopPolling(): void {
    this.isPolling = false;
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }
}
