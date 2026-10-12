import type { EpgProgramItem } from './LiveUtils';
import { parseXmltvDate } from './LiveUtils';
import { getMergedStopwords } from './StopwordsUtils';
import type { SearchMethodsConfig } from '$lib/api/types';

export interface IntelligentSearchResult {
  totalScore: number;
  hasMatch: boolean;
  bestProgram: EpgProgramItem | null;
}

/**
 * Normalizes text by converting to lowercase, optionally removing diacritics/accents and punctuation.
 *
 * @param text Source string to normalize.
 * @param stripDiacritics Whether Method C diacritics stripping is enabled.
 * @returns Normalized string.
 */
export function normalizeText(text: string, stripDiacritics = true): string {
  if (!text) return '';
  let str = text.toLowerCase();
  if (stripDiacritics) {
    str = str.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  }
  return str
    .replace(/[^\w\s]/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Splits query string into token keywords.
 *
 * @param query Raw query string.
 * @param stopwords Set of active stop-words to exclude.
 * @param useStopwords Whether Method B stop-words removal is enabled.
 * @param stripDiacritics Whether Method C diacritics stripping is enabled.
 * @returns Array of token strings.
 */
export function tokenizeQuery(
  query: string,
  stopwords: Set<string>,
  useStopwords = true,
  stripDiacritics = true
): string[] {
  const normalized = normalizeText(query, stripDiacritics);
  if (!normalized) return [];

  const rawTokens = normalized.split(' ');
  if (!useStopwords) {
    return rawTokens.filter((t) => t.length > 0);
  }

  const filtered = rawTokens.filter((token) => token.length > 0 && !stopwords.has(token));
  return filtered.length > 0 ? filtered : rawTokens.filter((t) => t.length > 0);
}

/**
 * Checks if a token matches within a target text string considering Method C (Word Boundary).
 *
 * @param text Target text string.
 * @param token Single query token keyword.
 * @param useWordBoundary Whether Method C word boundary matching is enabled.
 * @returns True if token matches.
 */
export function tokenMatchesText(text: string, token: string, useWordBoundary = true): boolean {
  if (!text || !token) return false;
  if (!useWordBoundary) {
    return text.includes(token);
  }
  try {
    const pattern = new RegExp(`(?:^|\\s|\\b)${token}`, 'i');
    return pattern.test(text);
  } catch {
    return text.includes(token);
  }
}

/**
 * Computes relevance score and time boost for an EPG programme.
 *
 * Methodologies controlled by SearchMethodsConfig:
 * - Method A: Relevance Scoring
 * - Method B: Stop-words Tokenization
 * - Method C: Diacritics Stripping & Whole-Word Boundary Match
 * - Method D: Time-Aware Boost
 *
 * @param program EPG programme item.
 * @param queryTokens Normalized query tokens.
 * @param methods Active search methods toggles.
 * @param referenceDate Base reference Date (defaults to now).
 * @returns Relevance score number.
 */
export function scoreProgrammeMatch(
  program: EpgProgramItem,
  queryTokens: string[],
  methods: SearchMethodsConfig = { method_a: true, method_b: true, method_c: true, method_d: true },
  referenceDate: Date = new Date()
): number {
  if (!program || queryTokens.length === 0) return 0;

  const useMethodA = methods.method_a !== false;
  const useMethodC = methods.method_c !== false;
  const useMethodD = methods.method_d !== false;

  const titleNorm = normalizeText(program.t || '', useMethodC);
  const descNorm = normalizeText(program.d || '', useMethodC);
  const fullTextNorm = `${titleNorm} ${descNorm}`;

  const allTokensMatch = queryTokens.every((token) => tokenMatchesText(fullTextNorm, token, useMethodC));
  if (!allTokensMatch) return 0;

  if (!useMethodA) {
    return 10;
  }

  let baseScore = 0;
  const rawQuery = queryTokens.join(' ');

  if (titleNorm === rawQuery) {
    baseScore += 100;
  } else if (tokenMatchesText(titleNorm, rawQuery, useMethodC)) {
    baseScore += 50;
  } else {
    queryTokens.forEach((token) => {
      if (tokenMatchesText(titleNorm, token, useMethodC)) baseScore += 25;
      else if (tokenMatchesText(descNorm, token, useMethodC)) baseScore += 10;
    });
  }

  if (useMethodD) {
    const pStart = parseXmltvDate(program.s);
    const pEnd = parseXmltvDate(program.e);

    if (pStart && pEnd) {
      const refMs = referenceDate.getTime();
      const startMs = pStart.getTime();
      const endMs = pEnd.getTime();

      if (refMs >= startMs && refMs <= endMs) {
        baseScore += 30;
      } else if (startMs > refMs && startMs - refMs <= 3 * 3600 * 1000) {
        baseScore += 15;
      }
    }
  }

  return baseScore;
}

/**
 * Searches and scores a channel's EPG programme array against query using active methodologies.
 *
 * @param programmes Array of EPG programme items for target channel.
 * @param query Raw search query string.
 * @param lang Primary language code (default 'it').
 * @param customStopwords User custom stop-words list.
 * @param methods Search methods config toggles.
 * @param referenceDate Base reference Date for time-aware scoring.
 * @returns IntelligentSearchResult object.
 */
export function searchProgrammesIntelligent(
  programmes: EpgProgramItem[] = [],
  query: string,
  lang = 'en',
  customStopwords: string[] = [],
  methods: SearchMethodsConfig = { method_a: true, method_b: true, method_c: true, method_d: true },
  referenceDate: Date = new Date()
): IntelligentSearchResult {
  if (!query || !query.trim() || !Array.isArray(programmes) || programmes.length === 0) {
    return { totalScore: 0, hasMatch: false, bestProgram: null };
  }

  const useMethodB = methods.method_b !== false;
  const useMethodC = methods.method_c !== false;

  const stopwords = getMergedStopwords(lang, customStopwords);
  const tokens = tokenizeQuery(query, stopwords, useMethodB, useMethodC);
  if (tokens.length === 0) {
    return { totalScore: 0, hasMatch: false, bestProgram: null };
  }

  let totalScore = 0;
  let bestProgram: EpgProgramItem | null = null;
  let highestScore = 0;

  programmes.forEach((prog) => {
    const score = scoreProgrammeMatch(prog, tokens, methods, referenceDate);
    if (score > 0) {
      totalScore += score;
      if (score > highestScore) {
        highestScore = score;
        bestProgram = prog;
      }
    }
  });

  return {
    totalScore,
    hasMatch: totalScore > 0,
    bestProgram
  };
}
