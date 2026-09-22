# ProMaster lateral development — tester handoff

## Start here

The earlier tested build demonstrated steering, then faulted after an
uninterrupted 8.868918-second request. Both full rlogs (segments 0 and 1) of
`06dc1eb54e298062/00000005--2c0b456823` were examined. This candidate limits
requests to 3.5 seconds and requires at least 2 seconds inactive with continuous
fault-free EPS standby before another handshake. Its reset behavior has not
yet been vehicle-validated. Do not repeat the existing 8.8-second faulting build.

Use `inauner/openpilot:master`. The `pm` and `promaster` branches are synchronized
aliases of the same tester revision; all three contain the same source and pin.
This candidate pins opendbc to `f989636a7b9b27038c1c0faa41d07620b6b86fde`,
[opendbc PR #3](https://github.com/inauner/opendbc/pull/3), based on PR #1.
The pin matters: updating only the outer repository or only Python files
does not establish that the corresponding panda safety firmware is running.

The primary torque cap is reduced from 300 to ±34 and secondary from 1,200
to ±136; driver/rate limits, matched-message safety, counter synchronization,
checksums, and EPS acknowledgment remain enforced. There is **no steering
assist during reset**. The high-level openpilot engagement may remain active
while actual steering requests and factory HUD state are inactive. If left
engaged, another handshake may begin after the reset requirements are met.
This is a short-engagement development candidate, not validated continuous
lane centering. See the
[evidence and limitations](https://github.com/inauner/opendbc/blob/f989636a7b9b27038c1c0faa41d07620b6b86fde/docs/promaster-request-duration.md).

Development now lives in `inauner/openpilot`, continuing the history at
`ab2666b3918ca664b8b3db7fe5a270e31ca208dc` with the updated opendbc pin and
this tester handoff. The temporary `inauner/promaster-dev` repository is
archived; use this repository for subsequent work.

### The recorded working baseline

The full rlogs identify openpilot `158241f5ac597ab74a57d4bc2f477f3eb0c19020`
and its opendbc gitlink `33d3ccec57446387a666599ca0094c39e08067e0`, from
[belm0's ProMaster test development](https://github.com/belm0/openpilot/commit/158241f5ac597ab74a57d4bc2f477f3eb0c19020).
That build demonstrated steering authority before the EPS fault. The name
`belm0/openpilot:promaster_test1` is movable: when checked on September 22,
its tip was `0fc08c699325677953c29fe4d4fc2873e41bcadb`, pinning a later
opendbc experiment `6676a00c396804d222f19ad06e0e31708f160ea8`. Do not use
that branch's current tip as a substitute for the recorded baseline.

Our outer openpilot runtime, model asset pointers, AGNOS 17.2 target, and all
submodule pins other than opendbc match the recorded build. Five malformed
symlinks introduced during the fork migration have been restored byte-for-byte
from that commit, fixing the spurious missing-LFS-object downloads. The opendbc
changes are the documented paired-message/driver-override fixes and conservative
request/reset and torque-limit changes; their acknowledgment/steering encoding
is based on the demonstrated path. This establishes a demonstrated starting
point, not vehicle validation of the new reset behavior.

## 1. Send this information before changing the installed software

Copy and fill in:

```text
Vehicle: model year / 1500, 2500 or 3500 / wheelbase / engine
Factory adaptive cruise control: yes / no / unknown
Factory lane keeping with steering intervention (not just warning): yes / no / unknown
Does factory lane keeping currently intervene normally?
Device: comma 3X / other
AGNOS version:
Current software repository, branch, and commit:
Harness model, connection location, and any wiring/SGW modifications:
Any pre-existing EPS, camera, ABS, or cruise faults?
Previous ProMaster test build, if any:
Exact symptom, dashboard/openpilot alert, and when it occurs:
Existing stock-reference route link and segments, if available:
Existing experimental engagement route link and segments, if available:
Can you use SSH and provide full rlogs?
Available bench or closed-course test setup:
```

Do not post a VIN, private SSH key, tokens, or unrestricted remote access.
If you are the owner of the already-supplied 2022 stock route, identify that
fact so we can reuse its baseline rather than asking for an identical drive.

From SSH on your own device, these commands only inspect the installation:

```sh
cat /VERSION
df -h /data
git -C /data/openpilot rev-parse HEAD
git -C /data/openpilot branch --show-current
git -C /data/openpilot status --short
git -C /data/openpilot submodule status opendbc_repo panda
```

Share the output privately with inauner. If a command fails, include the
error; do not reset the checkout or delete local changes to make it pass.

## 2. Optional: stage the source and collect a structured report

This creates a separate, incomplete source checkout. It does not install or
activate the experimental software. Run while parked/offroad with stable
power and Wi-Fi. If the target directory already exists, stop and use its
existing contents only after checking its commit; do not overwrite it.

```sh
GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 --single-branch \
  --branch master \
  https://github.com/inauner/openpilot.git /data/promaster-lateral-test1
cd /data/promaster-lateral-test1
git submodule update --init --depth 1 opendbc_repo
git rev-parse HEAD
git -C opendbc_repo rev-parse HEAD
```

The last command must print `f989636a7b9b27038c1c0faa41d07620b6b86fde`.
LFS assets and other submodules are deliberately not downloaded in this
preflight checkout. Do not run its launcher or point `/data/continue.sh` at it.

For a structured report, use the Python executable/environment normally used
by your **current active** openpilot installation:

```sh
cd /data/openpilot
python3 /data/promaster-lateral-test1/tools/promaster/collect_preflight.py
```

If your active installation uses `/usr/local/venv/bin/python`, substitute
that executable. The report reads version/commit information and selected
saved CarParams fields, including EPS firmware when available. It omits VINs,
account tokens, Git remote URLs, and keys. It does not contact panda or write
parameters. Saved CarParams can be stale; we confirm the actual vehicle and
safety configuration from a fresh route.

### Complete source and build preparation

To complete that staged checkout on Linux/AGNOS, use these commands from
`/data/promaster-lateral-test1` while offroad. They obtain the committed
dependencies and verify source completeness; they do not switch the active
installation or launch steering control. Git LFS must be installed.

```sh
git submodule sync --recursive
git submodule update --init --recursive --jobs 4
git lfs pull
git lfs fsck
python3 tools/promaster/verify_source.py
```

Require `source_complete: true` and no errors. The verifier checks the exact
opendbc pin, recursive submodule revisions, clean checkout, downloaded LFS
files, and the tested model/library symlinks. Stop on a failed command and
preserve its output; do not substitute branches or skip assets to continue.

On an AGNOS 17.2 device with the developer-confirmed setup, the repository's
standard dependency and build entry points are:

```sh
./tools/op.sh setup
./tools/op.sh build
```

These install dependencies and compile code. The build command selects the
device build process on AGNOS. Source verification is not a complete device
build or proof that the matching panda firmware is running. Keep the previous
installation and its exact commit available for rollback; switching the active
checkout/startup path remains a device-specific step after build/startup review.

## 3. Installation gate: return the preflight first

This source tree's `launch_env.sh` targets **AGNOS 17.2**. Its launcher can
initiate an OS update when `/VERSION` differs. We have not validated a full
device build or boot for the tester's current OS. Do not launch it on a
different AGNOS version, change the expected version to bypass the check,
or treat this staging procedure as an installation recipe.

After preflight review, the developer will provide an exact outer commit,
compatible OS/build procedure, installation and rollback steps for your
device. Preserve the previous working software and logs before that step.
This handoff provides staging, source verification and build preparation;
a bootable tester image and device-specific installation/rollback procedure
have not yet been validated.

The developer must verify that:

- The complete checkout, LFS assets, submodules and build match the specified
  revision; there is no stale prebuilt binary being reused.
- The panda build includes `fcaGiorgio` (this port is under `ALLOW_DEBUG`) and
  the running panda firmware signature matches the built firmware.
- Startup does not report missing processes, a failed build, invalid safety
  mode, CAN errors, relay malfunction, or existing vehicle faults.
- The logged vehicle is `RAM_PROMASTER` with `fcaGiorgio` safety. MOCK/noOutput
  cannot demonstrate openpilot torque; do not force a fingerprint or switch
  to allOutput to get around a mismatch.

The normal startup path can flash panda automatically when firmware differs.
Switching builds is therefore more than changing Python code. No manual
flashing commands or control-enabling parameter overrides are part of this
handoff.

## 4. Capture evidence in stages

**Next actuation test: short 3–4 second engagements first.** Prefer manual
cancellation at 3 seconds. At 3.5 seconds the candidate withdraws steering
requests even if still engaged; cancel before any automatic re-request.
Before extending the test, inspect full rlogs for paired inactive/zero torque,
continuous valid counters/checksums, and EPS returning cleanly from status 2
to 0 with LKA_FAULT remaining zero. On the next separate short engagement,
verify a new EPS acknowledgment before nonzero torque. Retain the intervening
inactive logs to measure the actual reset interval and standby behavior.

Stop on any EPS fault, oscillation, or unexpected steering. Save full logs and
EPS diagnostic codes if available; do not repeat the faulting run or increase
torque. A duration watchdog is the leading hypothesis, not a proven diagnosis:
oscillating torque and driver opposition remain plausible contributors.

**Existing logs first.** Send any route from a previous experimental
engagement, even if it only shows refusal to engage. Include the complete
route and the relevant segment numbers/time offsets. That may answer the
next question without another test.

**Passive baseline if missing.** Use the tester's known-working stock/passive
recording setup. Describe factory LKAS and ACC behavior, and record normal
operation without deliberately drifting out of a lane. Do not install this
experimental build just to obtain a baseline. A drive video alone is not
enough; we need raw CAN in full rlogs.

**Parked startup after the reviewed installation.** Record roughly one minute
with ignition on, the vehicle secured, and the driver at the controls. Note
recognition, alerts and existing warning lights. Do not force engagement or
assume that lack of steering while parked is a failure; speed/vehicle state
may inhibit EPS operation. Send this route before progressing to motion.

**Actuation testing comes after startup/log review and hardware validation.**
The developer and tester must agree a suitable bench or closed-course plan
for this exact vehicle. This document is not approval for public-road use.
Retain driver monitoring, the existing limits and acknowledgment gate; do not
increase torque, spoof speed, force controls_allowed, bypass faults or inject
raw steering CAN. Any unexpected steering, EPS warning, CAN/safety fault, or
failure to cancel ends that test. Preserve the route instead of repeating the
same failure. Do not handle a phone or terminal while driving.

For an agreed test, record the exact engagement/cancel times, displayed
alerts, approximate speed, whether any steering assist was felt and in which
direction. An observer can make notes. Do not tune parameters during the run.

## 5. Send a complete result packet

```text
Test ID/date:
Vehicle/device setup (or reference to previous preflight):
Outer repository commit:
opendbc commit:
AGNOS version:
Test stage: previous log / passive baseline / parked startup / agreed controlled test
Route link or route ID:
Segments supplied:
Full rlogs available: yes / no
Time offset of each engagement, alert, cancellation or unexpected behavior:
What the driver observed:
Any dashboard faults before/after:
Any software/settings/wiring changes since the previous result:
```

Keep the device on Wi-Fi after recording and confirm that the **full rlogs**
are accessible, not just qlogs/video. If cloud access is unavailable, copy
`rlog.zst`, `rlog.bz2`, or the completed `rlog` files from every relevant
segment under `/data/media/0/realdata` and share them privately. Include at
least the segment preceding the event, the event segment, and the following
segment when available. Copy completed segments rather than an actively
written log. Do not delete local logs until receipt is confirmed. Logs can
contain location and vehicle information; avoid public GitHub attachments.

## How the results drive the next change

| First failure in the log | Next development focus |
| --- | --- |
| Wrong vehicle or safety model | Firmware fingerprint, equipment and bus topology |
| Recognized but latActive never becomes true | Engagement prerequisites and logged events |
| Requests exist but panda rejects them | Exact rejected payloads, firmware and safety checks |
| Requests accepted, EPS stays at 0 | Stock/request/HUD sequence, bus routing, variant and status bits |
| EPS reaches 2 but torque stays zero | Controller input, driver torque and acknowledgment timing |
| Paired nonzero commands but no useful response | Measured EPS/steering response and protocol interpretation |

The supplied stock reference shows EPS acknowledgment around 10–31 ms, but
that is an observation, not a new timeout requirement. We change one evidenced
cause at a time and keep each test tied to exact commits.

Background: [comma's port structure](https://docs.comma.ai/how-to/car-port/)
and [safety requirements](https://docs.comma.ai/SAFETY/). The targeted tests
passed; that alone does not validate the complete port or physical steering.

## Validation status for this candidate

- Current targeted controller/safety/CAN checksum suites: 74 passed, 4 skipped,
  389 subtests passed, using locally compiled libsafety and the repository SCons
  build. Ruff and diff checks passed.
- New coverage includes exact deadline boundaries, complete/reset-interrupted
  standby, quick re-engagement, faults, stale and fresh acknowledgment, multiple
  cycles, both command checksums/counters, lower torque caps, and an 1,800-frame
  controller-to-safety sequence.
- No complete device build, panda flash, hardware-in-loop test, or physical
  validation of the 3.5/2-second protocol has been performed.

### Historical PR #1 validation

- Targeted ProMaster/controller/CAN checksum run: 66 passed, 4 skipped,
  389 subtests passed.
- Broader safety run: 2,747 passed, 1,455 skipped, 9,268 subtests passed.
  Two MISRA mutation tests failed to execute their shell checker because the
  isolated test copy had CRLF shell-script endings (`bash\r` not found).
  This is not a passing MISRA result; static safety analysis remains outstanding.
- Preflight collector: lint passed; synthetic saved-parameter checks verified
  EPS firmware extraction, VIN omission, and handling of malformed parameters.
- No complete tester-device build, OS migration, firmware flash, hardware-in-loop
  validation, or physical steering test has been completed. GitHub reported no
  CI checks on opendbc PR #1; the test results above were obtained locally in
  an isolated development directory on a comma 3X.
