/**
 * Controller managing debounced text input timer state.
 */
export class DebouncedInputController {
  private timer: ReturnType<typeof setTimeout> | null = null;

  /**
   * Schedules a debounced callback execution.
   *
   * @param value Target text input string value.
   * @param delayMs Delay duration in milliseconds.
   * @param callback Callback function to trigger after delay.
   */
  public handleInput(
    value: string,
    delayMs: number,
    callback: (val: string) => void
  ): void {
    if (this.timer) {
      clearTimeout(this.timer);
    }

    if (delayMs <= 0) {
      callback(value);
      return;
    }

    this.timer = setTimeout(() => {
      callback(value);
      this.timer = null;
    }, delayMs);
  }

  /**
   * Clears any active pending debounce timer.
   */
  public cancel(): void {
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
  }
}
