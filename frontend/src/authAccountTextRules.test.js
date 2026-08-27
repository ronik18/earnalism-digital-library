import fs from "fs";
import path from "path";

const source = (file) => fs.readFileSync(path.join(__dirname, file), "utf8");

const LOCKED_PRODUCT_SENTENCE = "Read the first 3 pages free. Listening requires an active Reading Pass.";

describe("auth and account customer-copy contract", () => {
  const login = source("pages/Login.jsx");
  const signup = source("pages/Signup.jsx");
  const account = source("pages/Account.jsx");

  test("retains the locked Reading Pass sentence on each applicable customer surface", () => {
    [login, signup, account].forEach((page) => expect(page).toContain(LOCKED_PRODUCT_SENTENCE));
  });

  test("uses library-wide Signup accessibility copy", () => {
    expect(signup).toContain("Create an account to manage your Reading Pass and return to your place across eligible books.");
    expect(signup).not.toContain("Dracula reading time");
  });

  test("uses library-wide Account empty and continuation copy while retaining existing actions", () => {
    expect(account).toContain("No reading activity yet. Open a book from the library to begin.");
    expect(account).toContain("Continue reading");
    expect(account).not.toContain("Open Dracula from the library");
    expect(account).not.toContain("Continue Dracula from the live shelf");
    expect(account).toContain('to="/reader/dracula"');
    expect(account).toContain('data-testid="account-logout"');
  });
});
