import { api } from '$lib/api/client';
import type { ChannelItem, ChannelRewritePayload, RewriteRule } from '$lib/api/types';
import { toastStore } from '$lib/stores/toastStore';

export class MetadataModalController {
  public saving = $state(false);
  public loading = $state(false);
  public channelRules = $state<RewriteRule[]>([]);

  /**
   * Loads individual rewrite rules for a target channel original URL.
   */
  public async loadChannelRules(channel: ChannelItem): Promise<RewriteRule[]> {
    this.loading = true;
    try {
      const cfg = await api.getConfig();
      const individualMap = cfg.individual_rewrites || {};
      this.channelRules = individualMap[channel.original_url] || [];
      return this.channelRules;
    } catch {
      this.channelRules = [];
      return [];
    } finally {
      this.loading = false;
    }
  }

  /**
   * Saves individual rewrite rules for a target channel.
   */
  public async saveChannelRules(channel: ChannelItem, rules: RewriteRule[]): Promise<boolean> {
    this.saving = true;
    try {
      const cfg = await api.getConfig();
      if (!cfg.individual_rewrites) cfg.individual_rewrites = {};

      if (rules.length === 0) {
        delete cfg.individual_rewrites[channel.original_url];
      } else {
        cfg.individual_rewrites[channel.original_url] = rules;
      }

      await api.updateConfig(cfg);
      toastStore.success(`Individual rewrites updated for '${channel.name}'.`);
      return true;
    } catch (err: any) {
      toastStore.error(`Failed to save rewrites: ${err.message}`);
      return false;
    } finally {
      this.saving = false;
    }
  }

  /**
   * Updates or removes an individual channel attribute rewrite rule via API.
   *
   * @param channel Target channel item.
   * @param field Target field name ('name' | 'group' | 'logo' | 'url' | 'user_agent').
   * @param newVal New value to assign.
   */
  public async updateRewrite(
    channel: ChannelItem,
    field: ChannelRewritePayload['field'],
    newVal: string
  ): Promise<boolean> {
    this.saving = true;
    try {
      const originalVal = (channel.original_data && channel.original_data[field as keyof typeof channel.original_data]) || '';
      await api.updateChannelRewrite({
        original_url: channel.original_url,
        field,
        original_val: String(originalVal),
        new_val: newVal.trim()
      });
      toastStore.success(`Updated '${field}' for channel '${channel.name}'.`);
      return true;
    } catch (err: any) {
      toastStore.error(`Failed to update ${field}: ${err.message}`);
      return false;
    } finally {
      this.saving = false;
    }
  }
}
