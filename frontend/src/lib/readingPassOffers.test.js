import { availableReadingPasses, presentReadingPass } from "./readingPassOffers";

const serverPack = {
  id: "30m",
  label: "The Opening Hour",
  minutes: 30,
  amount_paise: 4900,
  price_inr: 49,
  note: "Continue after the free preview, one careful sitting at a time.",
};

describe("Reading Pass offer contract", () => {
  test("accepts the backend PackOut shape without fabricating an expiry", () => {
    expect(presentReadingPass(serverPack)).toEqual(expect.objectContaining({
      ...serverPack,
      validity_days: null,
      unitPrice: "1.63",
    }));
  });

  test("retains an explicitly positive validity_days value and rejects an invalid one", () => {
    expect(presentReadingPass({ ...serverPack, validity_days: 30 })?.validity_days).toBe(30);
    expect(presentReadingPass({ ...serverPack, validity_days: 0 })).toBeNull();
    expect(presentReadingPass({ ...serverPack, validity_days: "30" })).toBeNull();
  });

  test("keeps required PackOut validation and duplicate suppression", () => {
    expect(presentReadingPass({ ...serverPack, label: "" })).toBeNull();
    expect(presentReadingPass({ ...serverPack, note: null })).toBeNull();
    expect(presentReadingPass({ ...serverPack, amount_paise: -1 })).toBeNull();
    expect(availableReadingPasses([serverPack, { ...serverPack }, { ...serverPack, id: "1h" }, null])).toHaveLength(2);
  });
});
