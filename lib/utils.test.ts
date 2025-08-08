import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { fetcher, nFormatter, capitalize, truncate, timeAgo } from "./utils";

const originalFetch = global.fetch;

describe("lib/utils", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
    global.fetch = originalFetch as any;
  });

  describe("fetcher", () => {
    it("returns JSON when response ok", async () => {
      const mockJson = { hello: "world" };
      global.fetch = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(mockJson) } as any);
      const res = await fetcher("https://example.com/api");
      expect(res).toEqual(mockJson);
      expect(global.fetch).toHaveBeenCalledWith("https://example.com/api", undefined);
    });

    it("throws error with json.error when not ok", async () => {
      const mockErr = { error: "Something broke" };
      global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 500, json: () => Promise.resolve(mockErr) } as any);
      await expect(fetcher("/bad")).rejects.toMatchObject({ message: mockErr.error, status: 500 });
    });

    it("throws generic error when not ok and no json.error", async () => {
      const mockErr = { message: "no error field" };
      global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 400, json: () => Promise.resolve(mockErr) } as any);
      await expect(fetcher("/bad2")).rejects.toThrowError("An unexpected error occurred");
    });
  });

  describe("nFormatter", () => {
    it("formats large numbers with suffix", () => {
      expect(nFormatter(0)).toBe("0");
      expect(nFormatter(532)).toBe("532");
      expect(nFormatter(1500)).toBe("1.5K");
      expect(nFormatter(2500000)).toBe("2.5M");
    });
  });

  describe("capitalize", () => {
    it("capitalizes first letter", () => {
      expect(capitalize("hello")).toBe("Hello");
      expect(capitalize("")).toBe("");
      // @ts-expect-error testing non-string passthrough
      expect(capitalize(undefined)).toBe(undefined);
    });
  });

  describe("truncate", () => {
    it("truncates longer strings", () => {
      expect(truncate("abcdef", 10)).toBe("abcdef");
      expect(truncate("abcdefghij", 5)).toBe("abcde...");
    });
  });

  describe("timeAgo", () => {
    it("renders ms distance with ago by default", () => {
      const now = new Date("2024-01-01T00:00:00Z");
      vi.setSystemTime(now);
      const earlier = new Date("2023-12-31T23:59:00Z");
      const res = timeAgo(earlier);
      // ms formats like 1m ago
      expect(res.endsWith("ago")).toBe(true);
      expect(/\d+[smhdwy] ago$/.test(res)).toBe(true);
    });

    it("omits 'ago' when timeOnly=true", () => {
      const now = new Date("2024-01-01T00:00:00Z");
      vi.setSystemTime(now);
      const earlier = new Date("2023-12-31T23:59:00Z");
      const res = timeAgo(earlier, true);
      expect(res.includes("ago")).toBe(false);
    });
  });
});