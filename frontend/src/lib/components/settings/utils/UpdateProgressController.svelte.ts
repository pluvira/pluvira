import { api } from '$lib/api/client';
import type { UpdateProgressDTO, UpdateSourceProgress } from '$lib/api/types';
import {
  createDefaultProgressDTO,
  formatLogLines,
  type FormattedLogLine
} from './UpdateProgressUtils';

export type LogFilterLevel = 'all' | 'errors' | 'warnings';

export class UpdateProgressController {
  public rawLogs = $state<string[]>([]);
  public progress = $state<UpdateProgressDTO>(createDefaultProgressDTO());
  public isRunning = $state(false);
  public logFilter = $state<LogFilterLevel>('all');
  public showRawConsole = $state(false);
  public autoScroll = $state(true);

  public get elapsedSeconds(): number {
    return this.progress.elapsed_seconds;
  }

  private pollInterval: ReturnType<typeof setInterval> | null = null;
  private isFetching = false;

  public formattedLogs = $derived.by<FormattedLogLine[]>(() => {
    const all = formatLogLines(this.rawLogs);
    if (this.logFilter === 'errors') {
      return all.filter((l) => l.level === 'error');
    }
    if (this.logFilter === 'warnings') {
      return all.filter((l) => l.level === 'warning' || l.level === 'error');
    }
    return all;
  });

  public m3uSources = $derived.by<UpdateSourceProgress[]>(() => {
    return (this.progress.sources || []).filter((s) => s.type === 'm3u');
  });

  public epgSources = $derived.by<UpdateSourceProgress[]>(() => {
    return (this.progress.sources || []).filter((s) => s.type === 'epg');
  });

  public async startMonitoring(resetState = true): Promise<void> {
    if (resetState) {
      this.progress = createDefaultProgressDTO();
      this.rawLogs = [];
    }
    this.isRunning = true;

    this.stopMonitoring();
    this.isRunning = true;

    await this.pollProgressAndLogs();

    this.pollInterval = setInterval(async () => {
      await this.pollProgressAndLogs();
    }, 1000);
  }

  private async pollProgressAndLogs(): Promise<void> {
    if (this.isFetching) return;
    this.isFetching = true;

    try {
      const [dto, logs] = await Promise.all([
        api.getUpdateProgress(),
        api.getSystemLogs(1000)
      ]);

      if (dto) {
        this.progress = dto;
        this.isRunning = dto.is_running;

        if (!dto.is_running && this.pollInterval) {
          this.stopTimers();
        }
      }

      if (logs && logs.length > 0) {
        const combined = [...this.rawLogs, ...logs];
        this.rawLogs = combined.length > 2000 ? combined.slice(combined.length - 2000) : combined;
      }
    } catch {
      // Ignore intermittent poll failure
    } finally {
      this.isFetching = false;
    }
  }

  public async triggerUpdateAndMonitor(mode = 'full'): Promise<void> {
    try {
      await api.triggerUpdate(mode);
    } catch {
      // Handled
    }
    await this.startMonitoring();
  }

  public setLogFilter(filter: LogFilterLevel): void {
    this.logFilter = filter;
  }

  public toggleRawConsole(): void {
    this.showRawConsole = !this.showRawConsole;
  }

  public clearLogs(): void {
    this.rawLogs = [];
  }

  public stopMonitoring(): void {
    this.isRunning = false;
    this.stopTimers();
  }

  private stopTimers(): void {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  }
}
