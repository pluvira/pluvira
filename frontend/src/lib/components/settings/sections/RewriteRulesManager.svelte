<script lang="ts">
  import type { RewriteRule } from '$lib/api/types';
  import Input from '../../ui/Input.svelte';
  import Select from '../../ui/Select.svelte';
  import Button from '../../ui/Button.svelte';
  import AccordionCard from '../../ui/AccordionCard.svelte';
  import { removeArrayItem, moveArrayItem } from '$lib/utils/arrayUtils';
  import {
    createDefaultRewriteRule,
    getAccordionOpenIndex,
    setAccordionOpenIndex
  } from '../utils/SettingsUtils';
  import { onMount } from 'svelte';

  interface Props {
    rules?: RewriteRule[] | null;
    title?: string;
    description?: string;
    storageKeyPrefix?: string;
    onchange?: (rules: RewriteRule[]) => void;
    class?: string;
  }

  let {
    rules = $bindable(),
    description = 'Rules applied sequentially to transform metadata attributes',
    storageKeyPrefix = 'rw_rules',
    onchange,
    class: className = ''
  }: Props = $props();

  let expandedIndex = $state<number | null>(null);

  onMount(() => {
    expandedIndex = getAccordionOpenIndex(storageKeyPrefix);
  });

  function setExpandedIndex(idx: number | null) {
    expandedIndex = idx;
    setAccordionOpenIndex(storageKeyPrefix, idx);
  }

  function addRule(e?: MouseEvent) {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    const current = Array.isArray(rules) ? rules : [];
    rules = [...current, createDefaultRewriteRule()];
    setExpandedIndex(rules.length - 1);
    onchange?.(rules);
  }

  function removeRule(index: number) {
    rules = removeArrayItem(rules, index);
    if (expandedIndex === index) setExpandedIndex(null);
    onchange?.(rules);
  }

  function moveRule(index: number, direction: number) {
    rules = moveArrayItem(rules, index, direction);
    const newIndex = index + direction;
    if (expandedIndex === index) setExpandedIndex(newIndex);
    else if (expandedIndex === newIndex) setExpandedIndex(index);
    onchange?.(rules);
  }

  function updateRulePattern(rule: RewriteRule, val: string) {
    rule.pattern = val;
    handleRuleChange();
  }

  function updateRuleReplacement(rule: RewriteRule, val: string) {
    rule.replacement = val;
    handleRuleChange();
  }

  function updateRuleDescription(rule: RewriteRule, val: string) {
    rule.description = val;
    handleRuleChange();
  }

  function handleRuleChange() {
    onchange?.(rules || []);
  }
</script>

<div class="flex flex-col gap-3 w-full {className}">
  <div class="flex items-center justify-between border-b border-border/30 pb-2">
    <span class="text-xs text-muted-foreground">{description}</span>
    <Button variant="primary" size="sm" onclick={(e) => addRule(e)} class="text-xs !py-1">
      + Add Rewrite Rule
    </Button>
  </div>

  {#if !rules || rules.length === 0}
    <div class="panel-box !items-center !justify-center !p-4 text-muted-foreground">
      No rewrite rules defined. Click "+ Add Rewrite Rule" to create one.
    </div>
  {:else}
    <div class="flex flex-col gap-3">
      {#each rules as rule, idx (rule.description || rule.field + '_' + rule.replacement + '_' + idx)}
        {@const isExpanded = expandedIndex === idx}
        {@const ruleTitle = rule.description || (rule.pattern ? `${rule.field.toUpperCase()}: ${rule.pattern} → ${rule.replacement}` : `${rule.field.toUpperCase()} → ${rule.replacement}`)}
        <AccordionCard
          title={`Rule #${idx + 1}: ${ruleTitle}`}
          open={isExpanded}
          ontoggle={(isOpen) => setExpandedIndex(isOpen ? idx : null)}
          badgeText={rule.enabled ? 'Enabled' : 'Disabled'}
          badgeVariant={rule.enabled ? 'success' : 'muted'}
          index={idx}
          totalCount={rules.length}
          onmoveup={() => moveRule(idx, -1)}
          onmovedown={() => moveRule(idx, 1)}
          ondelete={() => removeRule(idx)}
        >
          <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
            <Select
              label="Field"
              bind:value={rule.field}
              onchange={handleRuleChange}
              options={[
                { label: 'Channel Name', value: 'name' },
                { label: 'Group Title', value: 'group' },
                { label: 'Logo Image URL', value: 'logo' },
                { label: 'Stream URL', value: 'url' },
                { label: 'User-Agent', value: 'user_agent' }
              ]}
            />

            <Select
              label="Mode"
              bind:value={rule.mode}
              onchange={handleRuleChange}
              options={[
                { label: 'Regex Search', value: 'regex' },
                { label: 'Wildcard (*)', value: 'wildcard' },
                { label: 'Fixed Text', value: 'text' },
                { label: 'Replace (Set)', value: 'replace' }
              ]}
            />

            {#if rule.mode !== 'replace'}
              <Input
                label="Pattern / Search text"
                value={rule.pattern ?? ''}
                oninput={(e) => updateRulePattern(rule, (e.target as HTMLInputElement).value)}
                placeholder="e.g. (?i)\\s+(HD)"
              />
            {/if}

            <Input
              label="Replacement / Value"
              value={rule.replacement ?? ''}
              oninput={(e) => updateRuleReplacement(rule, (e.target as HTMLInputElement).value)}
              placeholder="Replacement value..."
            />
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-3 items-center">
            <Input
              label="Description (Optional)"
              value={rule.description ?? ''}
              oninput={(e) => updateRuleDescription(rule, (e.target as HTMLInputElement).value)}
              placeholder="Identify this rule..."
            />
            <label class="flex items-center gap-2 cursor-pointer text-muted-foreground mt-4 md:mt-0">
              <input
                type="checkbox"
                bind:checked={rule.enabled}
                onchange={handleRuleChange}
                class="rounded text-primary"
              />
              <span class="font-bold">Rule is Enabled</span>
            </label>
          </div>
        </AccordionCard>
      {/each}
    </div>
  {/if}
</div>
