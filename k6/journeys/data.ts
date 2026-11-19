/**
 * Test data for the Astronomy Shop (docs/workload-model.md, "Test data").
 * Values marked ASSUMPTION have no production data behind them.
 */

import { pick, uuid } from "../lib/random.ts";

export interface Address {
  streetAddress: string;
  city: string;
  state: string;
  country: string;
  zipCode: string;
}

/** The checkout form's prefilled address, as the browser sends it (spike §6). */
export const DEFAULT_ADDRESS: Address = {
  streetAddress: "1600 Amphitheatre Parkway",
  city: "Mountain View",
  state: "CA",
  country: "United States",
  zipCode: "94043",
};

const US_ADDRESSES: readonly Address[] = [
  DEFAULT_ADDRESS,
  {
    streetAddress: "1 Infinite Loop",
    city: "Cupertino",
    state: "CA",
    country: "United States",
    zipCode: "95014",
  },
  {
    streetAddress: "350 Fifth Avenue",
    city: "New York",
    state: "NY",
    country: "United States",
    zipCode: "10118",
  },
  {
    streetAddress: "233 S Wacker Dr",
    city: "Chicago",
    state: "IL",
    country: "United States",
    zipCode: "60606",
  },
];

/** Shipping treats any country other than US/USA/United States as international. */
const INTERNATIONAL_ADDRESSES: readonly Address[] = [
  {
    streetAddress: "Platz der Republik 1",
    city: "Berlin",
    state: "BE",
    country: "Germany",
    zipCode: "11011",
  },
  {
    streetAddress: "1-1 Chiyoda",
    city: "Tokyo",
    state: "13",
    country: "Japan",
    zipCode: "100-8111",
  },
  {
    streetAddress: "290 Bremner Blvd",
    city: "Toronto",
    state: "ON",
    country: "Canada",
    zipCode: "M5V 3L9",
  },
];

/**
 * ASSUMPTION: 20% of buyers ship internationally. Included in the baseline so the
 * `intlShippingSlowdown` fault (Phase 5) affects a known share of checkouts without changing the
 * workload between baseline and fault runs.
 */
export const INTERNATIONAL_SHARE = 0.2;

/** The checkout form's prefilled test card (VISA, passes the payment service's Luhn check). */
export const CREDIT_CARD = {
  creditCardNumber: "4432-8015-6152-0454",
  creditCardCvv: 672,
  creditCardExpirationMonth: 1,
  creditCardExpirationYear: 2030,
} as const;

/** One shopper's identity for one session. A new session is a new user. */
export interface Shopper {
  /** Browser-generated UUID used as both `sessionId` and `userId` (spike §6). */
  userId: string;
  email: string;
  address: Address;
  currency: "USD";
}

export function newShopper(roll: number = Math.random()): Shopper {
  const userId = uuid();
  return {
    userId,
    // example.com is reserved (RFC 2606); the demo's email service sends nothing externally.
    email: `shopper-${userId}@example.com`,
    address: roll < INTERNATIONAL_SHARE ? pick(INTERNATIONAL_ADDRESSES) : pick(US_ADDRESSES),
    // ASSUMPTION: everyone shops in USD, the demo's default. Currency switching is left out.
    currency: "USD",
  };
}
