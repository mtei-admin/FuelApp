/** Allowed: letters, numbers, hyphen, spaces, and "&". */
export const PLATE_INVALID_MESSAGE =
  'Plate number may only contain letters, numbers, hyphens, spaces, and "&".';

const PLATE_PATTERN = /^[A-Z0-9\-\s&]+$/;
const HAS_LETTER_OR_DIGIT = /[A-Z0-9]/;

/**
 * Validate and normalize a plate number for save.
 * Trims ends, uppercases, allows hyphen/space/&, rejects other specials.
 */
export function normalizePlateNumber(raw: string): string {
  const normalized = raw.trim().toUpperCase();
  if (!normalized) {
    throw new Error("Plate number is required.");
  }
  if (!PLATE_PATTERN.test(normalized) || !HAS_LETTER_OR_DIGIT.test(normalized)) {
    throw new Error(PLATE_INVALID_MESSAGE);
  }
  return normalized;
}
