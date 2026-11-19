/**
 * Shared checks. Check names follow `<endpoint> <what>`, e.g. `api_products_list status 200`,
 * so the `check` tag lines up with the `name` tag.
 */

import { check } from "k6";

import type { Response } from "./http.ts";

export function checkStatus(res: Response, name: string, expected = 200): boolean {
  return check(res, { [`${name} status ${expected}`]: (r) => r.status === expected }, { name });
}

/** Parse a JSON body, or return undefined (a failed parse is itself a failed check). */
export function jsonBody(res: Response): unknown {
  if (typeof res.body !== "string") {
    return undefined;
  }
  try {
    return JSON.parse(res.body) as unknown;
  } catch {
    return undefined;
  }
}

/** Check a property of the parsed JSON body. `what` describes it, e.g. "has products". */
export function checkJson(
  res: Response,
  name: string,
  what: string,
  predicate: (body: unknown) => boolean,
): boolean {
  return check(res, { [`${name} ${what}`]: (r) => predicate(jsonBody(r)) }, { name });
}

export function checkBodyIncludes(res: Response, name: string, text: string): boolean {
  return check(
    res,
    {
      [`${name} body includes ${JSON.stringify(text)}`]: (r) =>
        typeof r.body === "string" && r.body.includes(text),
    },
    { name },
  );
}
