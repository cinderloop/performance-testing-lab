/**
 * The only way lab scripts send HTTP requests. Each request:
 *  - is built from the configured base URL plus a path (absolute URLs are refused),
 *  - passes the local-target guard,
 *  - carries an explicit timeout (ADR 0008) and the tagging conventions (tags.ts),
 *  - declares which statuses count as success, so `expected_response` and `http_req_failed`
 *    mean "the request did what the user needed", not just "status < 400".
 */

import http from "k6/http";
import type { Params, RefinedResponse, RequestBody, ResponseType } from "k6/http";

import type { LabConfig } from "./config.ts";
import { assertLocalTarget } from "./guard.ts";
import { assertEndpointName, type EndpointGroup } from "./tags.ts";

export interface RequestSpec {
  /** Endpoint id, used as the `name` tag. */
  name: string;
  group: EndpointGroup;
  /** Statuses that count as success. Default: [200]. */
  expected?: readonly number[];
  /** Overrides the run's timeout for this request only. */
  timeoutMs?: number;
  tags?: Readonly<Record<string, string>>;
  headers?: Readonly<Record<string, string>>;
}

export type Response = RefinedResponse<ResponseType | undefined>;

const callbacks = new Map<string, ReturnType<typeof http.expectedStatuses>>();

function expectedCallback(statuses: readonly number[]): ReturnType<typeof http.expectedStatuses> {
  const key = statuses.join(",");
  let cb = callbacks.get(key);
  if (cb === undefined) {
    cb = http.expectedStatuses(...statuses);
    callbacks.set(key, cb);
  }
  return cb;
}

export interface Client {
  get(path: string, spec: RequestSpec): Response;
  post(path: string, body: RequestBody | null, spec: RequestSpec): Response;
  postJson(path: string, payload: unknown, spec: RequestSpec): Response;
}

export function createClient(config: LabConfig): Client {
  function url(path: string): string {
    if (!path.startsWith("/")) {
      throw new Error(`request paths must start with "/", got ${JSON.stringify(path)}`);
    }
    const full = config.baseUrl + path;
    assertLocalTarget(full);
    return full;
  }

  function params(spec: RequestSpec, extraHeaders: Record<string, string> = {}): Params {
    assertEndpointName(spec.name);
    return {
      timeout: spec.timeoutMs ?? config.timeoutMs,
      tags: { ...spec.tags, name: spec.name, endpoint_group: spec.group },
      headers: { ...extraHeaders, ...spec.headers },
      responseCallback: expectedCallback(spec.expected ?? [200]),
    };
  }

  return {
    get(path, spec) {
      return http.request("GET", url(path), null, params(spec));
    },
    post(path, body, spec) {
      return http.request("POST", url(path), body, params(spec));
    },
    postJson(path, payload, spec) {
      return http.request(
        "POST",
        url(path),
        JSON.stringify(payload),
        params(spec, { "Content-Type": "application/json" }),
      );
    },
  };
}
