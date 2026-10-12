import { api } from '$lib/api/client';
import { toastStore } from '$lib/stores/toastStore';

export class FactoryResetController {
  public step = $state<1 | 2>(1);
  public confirmText = $state('');
  public loading = $state(false);
  public errorMessage = $state<string | null>(null);

  public isConfirmValid = $derived(this.confirmText.trim() === 'RESET');

  public nextStep(): void {
    this.step = 2;
    this.errorMessage = null;
  }

  public prevStep(): void {
    this.step = 1;
    this.confirmText = '';
    this.errorMessage = null;
  }

  public reset(): void {
    this.step = 1;
    this.confirmText = '';
    this.errorMessage = null;
    this.loading = false;
  }

  public async executeReset(onSuccess?: () => void): Promise<boolean> {
    if (!this.isConfirmValid) {
      this.errorMessage = 'Please type "RESET" to confirm.';
      return false;
    }

    this.loading = true;
    this.errorMessage = null;

    try {
      const res = await api.factoryReset();
      if (res.success) {
        toastStore.success('Factory reset completed. All data and settings restored.');
        if (typeof window !== 'undefined') {
          window.localStorage.clear();
          window.sessionStorage.clear();
        }
        if (onSuccess) {
          onSuccess();
        }
        return true;
      } else {
        this.errorMessage = res.message || 'Factory reset failed.';
        toastStore.error(this.errorMessage);
        return false;
      }
    } catch (err: any) {
      const msg = err instanceof Error ? err.message : 'Factory reset request failed';
      this.errorMessage = msg;
      toastStore.error(msg);
      return false;
    } finally {
      this.loading = false;
    }
  }
}
