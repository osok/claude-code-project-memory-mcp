/**
 * Helper functions for common operations.
 */

/**
 * Generate a new unique identifier.
 *
 * @returns A new UUID-like string
 *
 * @example
 * const id = generateId();
 * // Returns something like "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
 */
export function generateId(): string {
  // Simple UUID v4-like generator
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * Format a date object as a string.
 *
 * @param date - The date to format
 * @param format - The format string to use (default: "YYYY-MM-DD HH:mm:ss")
 * @returns Formatted date string
 *
 * @example
 * formatDate(new Date(2024, 0, 15, 10, 30, 0))
 * // Returns "2024-01-15 10:30:00"
 */
export function formatDate(date: Date, format = 'YYYY-MM-DD HH:mm:ss'): string {
  const pad = (n: number): string => n.toString().padStart(2, '0');

  const year = date.getFullYear();
  const month = pad(date.getMonth() + 1);
  const day = pad(date.getDate());
  const hours = pad(date.getHours());
  const minutes = pad(date.getMinutes());
  const seconds = pad(date.getSeconds());

  return format
    .replace('YYYY', year.toString())
    .replace('MM', month)
    .replace('DD', day)
    .replace('HH', hours)
    .replace('mm', minutes)
    .replace('ss', seconds);
}

/**
 * Parse a string into a Date object.
 *
 * @param value - The string to parse
 * @returns Parsed Date or null if parsing fails
 *
 * @example
 * parseDate("2024-01-15") // Date object
 * parseDate("invalid") // null
 */
export function parseDate(value: string): Date | null {
  if (!value) {
    return null;
  }

  const date = new Date(value);
  return isNaN(date.getTime()) ? null : date;
}

/**
 * Convert text to a URL-friendly slug.
 *
 * @param text - The text to slugify
 * @param separator - Character to use between words (default: "-")
 * @param maxLength - Maximum length of the result (default: 100)
 * @returns URL-friendly slug
 *
 * @example
 * slugify("Hello World!") // "hello-world"
 * slugify("My Project Name", "_") // "my_project_name"
 */
export function slugify(
  text: string,
  separator = '-',
  maxLength = 100
): string {
  if (!text) {
    return '';
  }

  return text
    .toLowerCase()
    .trim()
    .replace(/[^\w\s-]/g, '') // Remove special characters
    .replace(/[\s_-]+/g, separator) // Replace spaces and separators
    .replace(new RegExp(`^${separator}|${separator}$`, 'g'), '') // Remove leading/trailing separators
    .slice(0, maxLength);
}

/**
 * Truncate text to a maximum length.
 *
 * @param text - The text to truncate
 * @param maxLength - Maximum length including suffix (default: 100)
 * @param suffix - String to append when truncated (default: "...")
 * @returns Truncated text
 *
 * @example
 * truncate("Hello World", 8) // "Hello..."
 */
export function truncate(
  text: string,
  maxLength = 100,
  suffix = '...'
): string {
  if (!text || text.length <= maxLength) {
    return text || '';
  }
  return text.slice(0, maxLength - suffix.length) + suffix;
}

/**
 * Return singular or plural form based on count.
 *
 * @param count - The count to check
 * @param singular - Singular form of the word
 * @param plural - Plural form (defaults to singular + "s")
 * @returns Appropriate form with count
 *
 * @example
 * pluralize(1, "task") // "1 task"
 * pluralize(5, "task") // "5 tasks"
 */
export function pluralize(
  count: number,
  singular: string,
  plural?: string
): string {
  const form = count === 1 ? singular : (plural ?? singular + 's');
  return `${count} ${form}`;
}

/**
 * Merge multiple objects.
 *
 * @param objects - Objects to merge
 * @returns Merged object
 *
 * @example
 * mergeObjects({ a: 1 }, { b: 2 }) // { a: 1, b: 2 }
 */
export function mergeObjects<T extends object>(...objects: Partial<T>[]): T {
  return Object.assign({}, ...objects) as T;
}

/**
 * Split an array into chunks of specified size.
 *
 * @param items - The array to split
 * @param chunkSize - Maximum size of each chunk
 * @returns Array of chunks
 *
 * @example
 * chunkArray([1, 2, 3, 4, 5], 2) // [[1, 2], [3, 4], [5]]
 */
export function chunkArray<T>(items: T[], chunkSize: number): T[][] {
  if (chunkSize <= 0) {
    throw new Error('chunkSize must be positive');
  }

  const chunks: T[][] = [];
  for (let i = 0; i < items.length; i += chunkSize) {
    chunks.push(items.slice(i, i + chunkSize));
  }
  return chunks;
}

/**
 * Safely get a nested value from an object.
 *
 * @param data - The object to traverse
 * @param path - Dot-separated path to the value
 * @param defaultValue - Default value if path not found
 * @returns The value at path or default
 *
 * @example
 * safeGet({ a: { b: 1 } }, "a.b") // 1
 * safeGet({ a: 1 }, "a.b.c", "missing") // "missing"
 */
export function safeGet<T>(
  data: Record<string, unknown>,
  path: string,
  defaultValue?: T
): T | undefined {
  const keys = path.split('.');
  let result: unknown = data;

  for (const key of keys) {
    if (result === null || result === undefined) {
      return defaultValue;
    }
    if (typeof result === 'object') {
      result = (result as Record<string, unknown>)[key];
    } else {
      return defaultValue;
    }
  }

  return (result as T) ?? defaultValue;
}

/**
 * Debounce a function.
 *
 * @param fn - The function to debounce
 * @param delay - Delay in milliseconds
 * @returns Debounced function
 */
export function debounce<T extends (...args: unknown[]) => unknown>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;

  return function (...args: Parameters<T>) {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    timeoutId = setTimeout(() => {
      fn(...args);
      timeoutId = null;
    }, delay);
  };
}

/**
 * Sleep for a specified duration.
 *
 * @param ms - Duration in milliseconds
 * @returns Promise that resolves after the duration
 */
export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
