# pokemon_cafe_booking

Selenium script that automates the Pokemon Cafe reservation site
(`reserve.pokemon-cafe.jp` for Tokyo, `osaka.pokemon-cafe.jp` for Osaka) up to
the point where a human needs to solve a captcha, then continues on to submit
a booking for the first available date/time slot it finds.

Run it with:

```sh
bazel run //packages/pokemon_cafe_booking:pokemon_cafe_booking
```

## Site flow (`create_booking` in `main.py`)

The reservation site walks through a fixed sequence of pages. Each "Step" in
`create_booking` drives one of them via Selenium `find_element`/`click`
calls, matched against the site's DOM by XPath:

1. **Agree to terms** -- check the `同意する` radio button and click
   `同意して進む`. Both elements are scrolled into view first
   (`scrollIntoView`) since they sit below the fold.
2. **Captcha challenge** -- see below, this is the part a human has to do.
3. **Make a reservation** -- click the arrow-down "make reservation" button.
4. **Guest count** -- select `n_guests` from the `guest` `<select>`.
5. **Calendar** -- read the calendar widget's text and parse it
   (`parse_calendar_text`) into a list of available dates for the current
   month; if none are available, click "next month" (`次の月を見る`) and
   parse again. If still nothing, the function returns early (nothing to
   book yet).
6. **Time slot** -- click the first available date, read the resulting
   timetable's text and parse it (`get_timetable`) into seat/time/grid-
   position tuples; click the first available slot.
7. **Contact form** -- fill in a hardcoded name/phone/email and stop just
   before actually submitting (the submit button's `is_displayed()` state is
   printed, but it isn't clicked).

`NoSuchElementException` at any point is swallowed silently (the page layout
didn't match what the script expected, so it just gives up quietly); any
other exception is re-raised with a `Failed to book for Tokyo: ...` message.
The browser is left open at the end (`driver.quit()` is commented out) so you
can see what state it ended up in.

## The captcha problem

Between steps 1 and 3, the site inserts an [AWS WAF CAPTCHA](https://docs.aws.amazon.com/waf/latest/developerguide/waf-captcha-and-challenge.html)
challenge that can't be solved programmatically -- solving it is the entire
point of a captcha. `_wait_for_captcha_success` exists to pause the automation
and let a human do that step in the actual open browser window:

- The captcha is served from a subdomain like
  `<hash>.captcha.awswaf.com`, but it's rendered as an overlay on the current
  page rather than a real navigation -- `driver.current_url` **stays on**
  `/reserve/auth_confirm` the whole time (before, during, and after the
  challenge is solved), so URL changes can't be used to detect completion.
- Solving the challenge shows a brief "Success" page, which then
  auto-redirects back through `/reserve/auth_confirm` and on into the normal
  reservation flow.
- Because that "Success" page can come and go faster than a slow poll would
  catch it, `_wait_for_captcha_success` polls (every `poll_interval` seconds,
  default 1) for **either** signal: the literal text `"Success"` appearing in
  `driver.page_source`, **or** the Step 3 "make reservation" button already
  being present (i.e. we've already bounced past the captcha entirely by the
  time we checked). Whichever shows up first ends the wait.
- `driver.page_source` only sees the top-level document. If the captcha
  widget's "Success" text turns out to live inside a cross-origin iframe, the
  text check won't fire directly -- but the fallback check on the Step 3
  button still catches completion once the page finishes bouncing back.
- The wait has a 10-minute ceiling (`timeout`); past that it raises
  `TimeoutException`, which is caught by `create_booking`'s generic
  `except Exception` handler like any other step failure.

## ChromeDriver: fetched, not checked in

`chromedriver_path()` resolves the path to the ChromeDriver binary that
Selenium's `Service` needs to launch Chrome. That binary isn't checked into
the repo (a previous version of this package vendored a Windows `.exe`, which
only worked by accident on Windows and not at all on macOS/Linux). Instead:

- `rules/third_party/chromedriver/repo.bzl` defines a `repository_rule` that
  downloads a pinned ChromeDriver release from
  [Chrome for Testing](https://googlechromelabs.github.io/chrome-for-testing/)
  for whichever OS/CPU Bazel is running on (`mac-arm64`, `mac-x64`, or
  `linux64`), and a `module_extension` that registers it as `@chromedriver`
  in `MODULE.bazel`.
- **ChromeDriver only works with a matching Chrome *major* version** (e.g.
  ChromeDriver 150.x refuses to drive Chrome 151). Since Chrome auto-updates
  independently of this repo, the pinned `_VERSION` in `repo.bzl` will
  eventually drift out of sync -- if `bazel run` fails with
  `SessionNotCreatedException: ... only supports Chrome version N`, bump
  `_VERSION` (and the `sha256`s, computed by downloading each
  `chromedriver-<platform>.zip` and running `shasum -a 256` over it) to a
  release matching your installed Chrome's major version.
- `BUILD.bazel` depends on `@chromedriver` as `data` and passes its runfiles
  location to the binary via the `CHROMEDRIVER_RLOCATIONPATH` environment
  variable, using the `$(rlocationpath @chromedriver//:chromedriver)` Make
  variable. This is necessary because the actual on-disk path only exists
  once Bazel has assembled the runfiles tree at run time -- it can't be
  hardcoded at build time.
- `chromedriver_path()` reads that environment variable and resolves it to a
  real filesystem path via the `bazel-runfiles` PyPI package's `Runfiles`
  API (`requirement("bazel-runfiles")` in `BUILD.bazel`). This is the PyPI
  twin of `@rules_python//python/runfiles` -- it's used instead of the
  pure-Bazel target specifically so the same import (`from runfiles import
  Runfiles`) also resolves for IDE tooling (mypy/Pyright) reading from the
  Poetry venv, not just under `bazel run`.
