import { api } from '$lib/api/client';
import { authStore } from '$lib/stores/authStore';
import { toastStore } from '$lib/stores/toastStore';

export class LoginController {
  public username = $state('');
  public password = $state('');
  public loading = $state(false);
  public errorMessage = $state<string | null>(null);

  /**
   * Submits credentials to the login API and persists JWT token.
   *
   * @returns Boolean indicating login success.
   */
  public async handleLogin(): Promise<boolean> {
    if (!this.username.trim() || !this.password.trim()) {
      this.errorMessage = 'Please enter both username and password.';
      return false;
    }

    this.loading = true;
    this.errorMessage = null;

    try {
      const result = await api.login(this.username.trim(), this.password.trim());
      const token = result.access_token || '';
      const user = this.username.trim();

      if (token) {
        authStore.login(token, user);
        toastStore.success(`Welcome back, ${user}!`);
        return true;
      } else {
        this.errorMessage = 'Invalid server response: missing token.';
        return false;
      }
    } catch (err: any) {
      this.errorMessage = err.message || 'Login failed. Please check your credentials.';
      toastStore.error(`Login failed: ${this.errorMessage}`);
      return false;
    } finally {
      this.loading = false;
    }
  }
}
