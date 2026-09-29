import fs from "fs";
import path from "path";

const source = (file) => fs.readFileSync(path.join(__dirname, file), "utf8");

const AUTH_PRODUCT_ACCESS_COPY = "The first 3 pages are free where a preview is available. A Reading Pass is required from page 4 on eligible titles. Listening appears only where an edition is approved.";

describe("auth and account customer-copy contract", () => {
  const authShell = source("components/AuthPageShell.jsx");
  const login = source("pages/Login.jsx");
  const signup = source("pages/Signup.jsx");
  const account = source("pages/Account.jsx");

  test("uses durable release-safe Reading Pass and listening policy copy across auth surfaces", () => {
    expect(authShell).toContain("AUTH_PRODUCT_ACCESS_COPY");
    [login, signup].forEach((page) => {
      expect(page).toContain("AUTH_PRODUCT_ACCESS_COPY");
      expect(page).not.toContain("Pass purchases are not available yet.");
    });
    expect(AUTH_PRODUCT_ACCESS_COPY).toContain("Reading Pass is required from page 4 on eligible titles.");
    expect(AUTH_PRODUCT_ACCESS_COPY).toContain("Listening appears only where an edition is approved.");
    expect(account).not.toContain(AUTH_PRODUCT_ACCESS_COPY);
  });

  test("uses library-wide Signup accessibility copy", () => {
    expect(signup).toContain("Create an account to manage your Reading Pass and return to your place across eligible books.");
    expect(signup).not.toContain("Dracula reading time");
  });

  test("uses library-wide Account empty copy and does not fabricate a saved continuation", () => {
    expect(account).toContain("No reading activity yet. Open a book from the library to begin.");
    expect(account).toContain("Browse the Library");
    expect(account).not.toContain("Open Dracula from the library");
    expect(account).not.toContain("Continue Dracula from the live shelf");
    expect(account).not.toContain('to="/reader/dracula"');
    expect(account).toContain('to="/library"');
    expect(account).toContain('data-testid="account-logout"');
  });
});
