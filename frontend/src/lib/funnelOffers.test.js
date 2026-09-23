import { canShowReaderFinishPrompt, markReaderFinishPromptShown } from "./funnelOffers";

test("reader finish prompt is session-memory only", () => {
  const storageSpy = jest.spyOn(Storage.prototype, "setItem");
  expect(canShowReaderFinishPrompt()).toBe(true);
  markReaderFinishPromptShown();
  expect(canShowReaderFinishPrompt()).toBe(false);
  expect(storageSpy).not.toHaveBeenCalled();
  storageSpy.mockRestore();
});
