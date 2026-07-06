# Security Policy

## Supported versions

Only the latest released version is supported. Security fixes are not
backported to older releases — please upgrade before reporting an
issue if you're not already on the latest version.

## Reporting a vulnerability

Please **do not** open a public issue for a security vulnerability.

Instead, use GitHub's private vulnerability reporting:

1. Go to the **Security** tab of this repository
2. Click **Report a vulnerability**

This opens a private advisory visible only to the maintainer, so
details aren't public before a fix is available.

If that isn't available to you for some reason, open a regular issue
asking to be contacted privately, without describing the vulnerability
itself.

## Scope

This integration fetches public, unauthenticated weather data from
[aviationweather.gov](https://aviationweather.gov/) and stores no
credentials or personal data of its own. Realistic concerns here are
things like: a malicious or spoofed API response causing a crash or
unexpected behavior, dependency vulnerabilities, or issues in the
generated airport/FIR data pipeline (`scripts/`) — all still worth
reporting.
