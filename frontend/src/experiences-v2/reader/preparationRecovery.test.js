import { preparationRetrySeconds } from './preparationRecovery';
const failure = (seconds, code = 'PREPARATION_EXPIRED', status = 403) => ({ response: { status, data: { detail: { code, retry_after_seconds: seconds } } } });
test.each([0,1,119,120])('accepts bounded server timing %s without granting access', seconds => {
  expect(preparationRetrySeconds(failure(seconds))).toBe(seconds);
});
test.each([undefined,null,-1,121,1.5,true,'120',Infinity,NaN])('ignores malformed/unbounded timing %s', seconds => {
  expect(preparationRetrySeconds(failure(seconds))).toBeNull();
});
test('unrelated denials and missing responses never become preparation advice', () => {
  expect(preparationRetrySeconds(failure(30,'CONTENT_REVOKED'))).toBeNull();
  expect(preparationRetrySeconds(failure(30,'PREPARATION_EXPIRED',200))).toBeNull();
  expect(preparationRetrySeconds(new Error('offline'))).toBeNull();
});
