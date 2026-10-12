import type { Component } from 'svelte';
import {
  Sparkles,
  Zap,
  Crown,
  Box,
  Bot,
  Shield,
  ShieldCheck,
  Users,
  Server,
  Cpu,
  Tv,
  Radio,
  Star,
  Flame,
  Activity,
  Heart,
  Building2,
  Award,
  UserCheck
} from '@lucide/svelte';

/**
 * Semantic color token mapper for subscription tiers.
 * Maps API color tokens to static Tailwind CSS v4 utility classes to ensure JIT compiler inclusion.
 */

export const TIER_BADGE_CLASSES: Record<string, string> = {
  cyan: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20',
  indigo: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20',
  amber: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
  emerald: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
  purple: 'text-purple-400 bg-purple-500/10 border-purple-500/20',
  rose: 'text-rose-400 bg-rose-500/10 border-rose-500/20',
  zinc: 'text-zinc-400 bg-zinc-500/10 border-zinc-500/20'
};

/**
 * Resolves static Tailwind CSS classes for a given tier badge color token.
 * Falls back to 'cyan' if token is missing or unrecognized.
 *
 * @param colorToken Semantic color name ('cyan', 'indigo', 'amber', 'emerald', 'purple', 'rose', 'zinc')
 * @returns Space-separated Tailwind utility classes for text, background, and border
 */
export function getTierBadgeClass(colorToken?: string | null): string {
  if (!colorToken || typeof colorToken !== 'string') {
    return TIER_BADGE_CLASSES.cyan;
  }
  const token = colorToken.trim().toLowerCase();
  return TIER_BADGE_CLASSES[token] || TIER_BADGE_CLASSES.cyan;
}

/**
 * Official Lucide icon catalog and legacy alias mapping for subscription tiers.
 */
export const TIER_BADGE_ICONS: Record<string, Component> = {
  sparkles: Sparkles,
  zap: Zap,
  crown: Crown,
  box: Box,
  bot: Bot,
  shield: Shield,
  'shield-check': ShieldCheck,
  users: Users,
  family: Users,
  team: Users,
  server: Server,
  cpu: Cpu,
  tv: Tv,
  radio: Radio,
  star: Star,
  flame: Flame,
  activity: Activity,
  heart: Heart,
  'building-2': Building2,
  building: Building2,
  enterprise: Building2,
  award: Award,
  partner: Award,
  'user-check': UserCheck
};

/**
 * Resolves static Lucide icon component for a given tier badge icon slug.
 * Falls back to UserCheck for free tier when no slug is provided, or Sparkles by default.
 *
 * @param iconSlug Normalized icon slug from SaaS tier descriptor
 * @param tier Optional subscription tier identifier
 * @returns Svelte icon Component
 */
export function getTierBadgeIcon(iconSlug?: string | null, tier?: string | null): Component {
  const slug = (iconSlug || '').trim().toLowerCase();
  if (slug && TIER_BADGE_ICONS[slug]) {
    return TIER_BADGE_ICONS[slug];
  }
  if (!slug && tier === 'free') {
    return UserCheck;
  }
  return Sparkles;
}
