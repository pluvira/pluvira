import { shouldConfirmDelete } from '$lib/utils/preferences';
import type { DeleteConfirmScope } from './ConfirmUtils';

export class ConfirmController {
  public open = $state(false);
  public scope = $state<DeleteConfirmScope>('history_record');
  private pendingAction: (() => void) | null = null;

  /**
   * Triggers delete confirmation dialog or executes action immediately if preference disabled.
   */
  public requestConfirm(scope: DeleteConfirmScope, action: () => void): void {
    if (!shouldConfirmDelete(scope)) {
      action();
    } else {
      this.scope = scope;
      this.pendingAction = action;
      this.open = true;
    }
  }

  /**
   * Executes the pending delete action upon dialog confirmation.
   */
  public handleConfirm(): void {
    if (this.pendingAction) {
      const action = this.pendingAction;
      this.pendingAction = null;
      action();
    }
  }
}
