export type DeleteConfirmScope =
  | 'history_record'
  | 'history_all'
  | 'iptv_source'
  | 'epg_source'
  | 'rewrite_rule'
  | 'override_rule'
  | 'notification_url'
  | 'scheduled_job'
  | 'system_job_disable'
  | 'scheduler_restore_defaults'
  | 'master_merge'
  | 'bulk_unmerge'
  | 'quarantined_streams'
  | 'filter_reset'
  | 'bulletin_single'
  | 'bulletin_archived_all';

import {
  shouldConfirmDelete,
  setDeleteConfirmationPreference,
  resetDeleteConfirmations
} from '$lib/utils/preferences';

export { shouldConfirmDelete, setDeleteConfirmationPreference, resetDeleteConfirmations };

export interface DeleteConfirmScopeDetails {
  scope: DeleteConfirmScope;
  title: string;
  message: string;
  dontAskText: string;
  confirmText?: string;
  confirmVariant?: 'danger' | 'primary' | 'secondary';
}

export const DELETE_CONFIRM_DETAILS: Record<DeleteConfirmScope, DeleteConfirmScopeDetails> = {
  history_record: {
    scope: 'history_record',
    title: 'Delete History Record',
    message: 'Are you sure you want to delete this execution history record?',
    dontAskText: "Don't ask again for single history record deletions"
  },
  history_all: {
    scope: 'history_all',
    title: 'Clear Execution History',
    message: 'Are you sure you want to clear all execution history records? This action cannot be undone.',
    dontAskText: "Don't ask again for clearing all history"
  },
  iptv_source: {
    scope: 'iptv_source',
    title: 'Delete IPTV Source',
    message: 'Are you sure you want to delete this IPTV M3U source configuration?',
    dontAskText: "Don't ask again for IPTV source deletions"
  },
  epg_source: {
    scope: 'epg_source',
    title: 'Delete EPG Source',
    message: 'Are you sure you want to delete this XMLTV EPG guide source configuration?',
    dontAskText: "Don't ask again for EPG source deletions"
  },
  rewrite_rule: {
    scope: 'rewrite_rule',
    title: 'Delete Rewrite Rule',
    message: 'Are you sure you want to delete this metadata rewrite rule?',
    dontAskText: "Don't ask again for rewrite rule deletions"
  },
  override_rule: {
    scope: 'override_rule',
    title: 'Delete EPG Mapping Override',
    message: 'Are you sure you want to delete this manual EPG mapping override rule?',
    dontAskText: "Don't ask again for EPG override rule deletions"
  },
  notification_url: {
    scope: 'notification_url',
    title: 'Delete Notification URL',
    message: 'Are you sure you want to delete this notification endpoint URL?',
    dontAskText: "Don't ask again for notification URL deletions"
  },
  scheduled_job: {
    scope: 'scheduled_job',
    title: 'Delete Scheduled Job',
    message: 'Are you sure you want to delete this background scheduled job?',
    dontAskText: "Don't ask again for scheduled job deletions"
  },
  system_job_disable: {
    scope: 'system_job_disable',
    title: 'Disable System Task',
    message: 'Disabling this system task may affect background license renewal, auto-sync, or daemon health. Are you sure you want to disable it?',
    dontAskText: "Don't ask again when disabling system tasks",
    confirmText: 'Disable Task',
    confirmVariant: 'danger'
  },
  scheduler_restore_defaults: {
    scope: 'scheduler_restore_defaults',
    title: 'Restore Default Tasks',
    message: 'Are you sure you want to restore factory default scheduler tasks? Custom tasks will be preserved.',
    dontAskText: "Don't ask again when restoring default tasks",
    confirmText: 'Restore Defaults',
    confirmVariant: 'primary'
  },
  master_merge: {
    scope: 'master_merge',
    title: 'Unmerge Master Channel',
    message: 'Are you sure you want to unmerge this master channel and restore separate streams?',
    dontAskText: "Don't ask again for master channel unmerging"
  },
  bulk_unmerge: {
    scope: 'bulk_unmerge',
    title: 'Unmerge All Master Channels',
    message: 'Are you sure you want to unmerge all active master channels in bulk?',
    dontAskText: "Don't ask again for bulk unmerging"
  },
  quarantined_streams: {
    scope: 'quarantined_streams',
    title: 'Purge Quarantined Streams',
    message: 'Are you sure you want to purge and remove all offline quarantined streams across your channels?',
    dontAskText: "Don't ask again for purging quarantined streams"
  },
  filter_reset: {
    scope: 'filter_reset',
    title: 'Reset Active Filters',
    message: 'Are you sure you want to reset all channel filters and reload the complete list?',
    dontAskText: "Don't ask again for resetting filters"
  },
  bulletin_single: {
    scope: 'bulletin_single',
    title: 'Delete Notice',
    message: 'Are you sure you want to permanently delete this archived system notice?',
    dontAskText: "Don't ask again for single notice deletions"
  },
  bulletin_archived_all: {
    scope: 'bulletin_archived_all',
    title: 'Delete All Archived Notices',
    message: 'Are you sure you want to permanently delete all archived system notices? This action cannot be undone.',
    dontAskText: "Don't ask again for deleting all archived notices"
  }
};
