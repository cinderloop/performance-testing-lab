/**
 * Local-target guard (ground rule 3).
 *
 * Every script validates its base URL at init, and every request URL before sending, so a
 * mistyped or malicious target fails before any traffic leaves k6. Pure TypeScript with no k6
 * imports, so the unit tests run under Node.
 *
 * The rule is an allowlist of exact host names, deliberately strict: no IPv6 literals, no
 * user-info (`user@host`), no trailing dots, no other loopback addresses, http/https only.
 */

/** Hosts that always mean "this machine". */
export const LOOPBACK_HOSTS: readonly string[] = ["localhost", "127.0.0.1"];

/**
 * Docker hostnames of the local demo, reachable only from inside its Docker network
 * (ADR 0001: k6 runs in a container on that network). Configured here, in the repo, and not
 * through an environment variable, so a run can't widen the allowlist.
 */
export const LOCAL_DOCKER_HOSTS: readonly string[] = ["frontend-proxy"];

export const ALLOWED_HOSTS: readonly string[] = [...LOOPBACK_HOSTS, ...LOCAL_DOCKER_HOSTS];

export class TargetNotAllowedError extends Error {
  constructor(url: string, reason: string) {
    super(`refusing non-local target ${JSON.stringify(url)}: ${reason}`);
    this.name = "TargetNotAllowedError";
  }
}

export interface ParsedTarget {
  scheme: "http" | "https";
  host: string;
  port: number | null;
}

const URL_RE = /^(https?):\/\/([^/?#]*)([/?#].*)?$/i;
const HOST_RE = /^[a-z0-9.-]+$/;

/** Split an absolute http(s) URL into scheme, host and port, or throw. */
export function parseTarget(url: string): ParsedTarget {
  const m = URL_RE.exec(url);
  if (m === null) {
    throw new TargetNotAllowedError(url, "not an absolute http:// or https:// URL");
  }
  const scheme = (m[1] ?? "").toLowerCase() as "http" | "https";
  const authority = m[2] ?? "";
  if (authority.includes("@")) {
    throw new TargetNotAllowedError(url, "user-info in URLs is not allowed");
  }
  if (authority.startsWith("[")) {
    throw new TargetNotAllowedError(url, "IPv6 literals are not allowed");
  }
  const colon = authority.lastIndexOf(":");
  const rawHost = colon === -1 ? authority : authority.slice(0, colon);
  const rawPort = colon === -1 ? null : authority.slice(colon + 1);
  const host = rawHost.toLowerCase();
  if (host === "" || !HOST_RE.test(host)) {
    throw new TargetNotAllowedError(url, `invalid host ${JSON.stringify(rawHost)}`);
  }
  let port: number | null = null;
  if (rawPort !== null) {
    if (!/^\d{1,5}$/.test(rawPort) || Number(rawPort) < 1 || Number(rawPort) > 65535) {
      throw new TargetNotAllowedError(url, `invalid port ${JSON.stringify(rawPort)}`);
    }
    port = Number(rawPort);
  }
  return { scheme, host, port };
}

/** Throw unless `url` targets one of the allowed local hosts. Returns the parsed target. */
export function assertLocalTarget(
  url: string,
  allowed: readonly string[] = ALLOWED_HOSTS,
): ParsedTarget {
  const target = parseTarget(url);
  if (!allowed.includes(target.host)) {
    throw new TargetNotAllowedError(
      url,
      `host ${JSON.stringify(target.host)} is not in the local allowlist [${allowed.join(", ")}]`,
    );
  }
  return target;
}
