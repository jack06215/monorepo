// Self-hosted (global) Renovate config, consumed by .github/workflows/renovate.yml.
//
// This is distinct from .github/renovate.json5: that one holds the *repository*
// rules (what to update, how to group, when). This one holds settings that only
// make sense for the runner itself and that a repo config is not permitted to set.

// Optional per-run override of the release-age gate, fed by the
// `minimumReleaseAge` workflow_dispatch input. Blank means "use the committed
// value in .github/renovate.json5".
//
// This has to travel through `force` rather than a plain
// RENOVATE_MINIMUM_RELEASE_AGE env var: Renovate ranks repository config ABOVE
// environment variables, so an env var would be silently outranked by the
// committed value. `force` is the one level that beats repo config.
const releaseAgeOverride = (process.env.RENOVATE_X_MIN_RELEASE_AGE || "").trim();

module.exports = {
  platform: "github",
  repositories: ["jack06215/monorepo"],

  // Renovate's default author is renovate@whitesourcesoftware.com, an address
  // owned by Mend with Vigilant Mode enabled -- every commit from it lands
  // marked "Unverified". Using an identity tied to this account lets GitHub
  // attribute and sign the commits instead.
  //
  // Trade-off: dependency bumps will read as authored by you. To keep them
  // visibly bot-authored (at the cost of staying unverified), swap in:
  //   "renovate[bot] <29139614+renovate[bot]@users.noreply.github.com>"
  gitAuthor: "Jack Cho <jack06215@gmail.com>",

  // Post-upgrade commands are refused unless they match one of these regexes.
  // Renovate deliberately makes this global-only so a repo config can never
  // grant itself arbitrary command execution.
  //
  // Option name confirmed against docs.renovatebot.com/self-hosted-configuration
  // (July 2026). Formerly `allowedPostUpgradeCommands`; if you ever pin an older
  // Renovate that predates the rename, this silently no-ops and requirements.txt
  // stops being regenerated.
  allowedCommands: ["^poetry (self add poetry-plugin-export|export) ?.*$"],

  // A config file is already committed, so skip the onboarding PR entirely.
  onboarding: false,
  requireConfig: "required",

  // Spread in only when the input was actually supplied, so the committed
  // 10-day gate stays in charge on every scheduled run.
  ...(releaseAgeOverride
    ? { force: { minimumReleaseAge: releaseAgeOverride } }
    : {}),
};
