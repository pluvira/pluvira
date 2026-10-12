/**
 * Multilingual stop-words dictionaries for EPG programme search filtering.
 */

export const STOPWORDS_BY_LANG: Record<string, string[]> = {
  en: [
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 'has', 'he',
    'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the', 'to', 'was', 'were', 'will', 'with'
  ],
  it: [
    'a', 'al', 'alla', 'alle', 'agli', 'col', 'coi', 'da', 'dal', 'dalla', 'dalle',
    'dello', 'degli', 'di', 'del', 'della', 'delle', 'in', 'nel', 'nella', 'nelle',
    'negli', 'su', 'sul', 'sulla', 'sulle', 'sugli', 'il', 'lo', 'la', 'i', 'gli',
    'le', 'un', 'uno', 'una', 'ed', 'e', 'o', 'ma', 'se', 'per', 'con', 'tra', 'fra'
  ],
  es: [
    'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'y', 'e', 'o', 'u',
    'de', 'del', 'a', 'al', 'en', 'con', 'por', 'para', 'sin', 'sobre', 'tras'
  ],
  fr: [
    'le', 'la', 'les', 'un', 'une', 'des', 'et', 'ou', 'de', 'du', 'en', 'dans',
    'avec', 'pour', 'par', 'sur', 'sous', 'ce', 'cette', 'ces'
  ],
  de: [
    'der', 'die', 'das', 'den', 'dem', 'des', 'ein', 'eine', 'einen', 'einem',
    'einer', 'und', 'oder', 'in', 'im', 'an', 'am', 'auf', 'mit', 'für', 'von'
  ],
  pt: [
    'o', 'a', 'os', 'as', 'um', 'uma', 'uns', 'umas', 'e', 'ou', 'de', 'do',
    'da', 'dos', 'das', 'em', 'no', 'na', 'nos', 'nas', 'com', 'por', 'para'
  ]
};

/**
 * Returns merged Set of stop-words combining primary language, English defaults, and custom words.
 *
 * @param lang Primary language code (default 'en').
 * @param customWords User custom stop-words list.
 * @returns Set of normalized lowercase stop-words.
 */
export function getMergedStopwords(lang = 'en', customWords: string[] = []): Set<string> {
  const merged = new Set<string>();

  const primaryList = STOPWORDS_BY_LANG[lang.toLowerCase()] || STOPWORDS_BY_LANG['en'];
  primaryList.forEach((word) => merged.add(word.toLowerCase()));

  const englishList = STOPWORDS_BY_LANG['en'] || [];
  englishList.forEach((word) => merged.add(word.toLowerCase()));

  if (Array.isArray(customWords)) {
    customWords.forEach((word) => {
      if (word && word.trim()) {
        merged.add(word.trim().toLowerCase());
      }
    });
  }

  return merged;
}
