import { unwrapSuccess } from "../unwrap";
import { ApiError } from "../mutator";

it.each([200, 201, 202, 204] as const)(
  "成功status %s の本文を返す",
  (status) => {
    const data = { id: 8 };
    expect(unwrapSuccess({ status, data }, status)).toBe(data);
  },
);
it.each([404, 413, 415, 422, 500])(
  "想定外status %s を成功として扱わない",
  (status) => {
    expect(() =>
      unwrapSuccess({ status, data: { code: "E_UNKNOWN" } }, 200),
    ).toThrow(ApiError);
  },
);
