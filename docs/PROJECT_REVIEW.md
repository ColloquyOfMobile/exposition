# Project Review and Next Steps

Reviewed 2026-09-26 at commit `59c4af3` on `Refactor`.

The [electronics follow-up review](ELECTRONICS_REVIEW.md), dated 2026-09-27, adds schematic/PCB checks, manufacturer-datasheet verification, and specific v2 fabrication blockers.

## Assessment

The project has substantial working behavior, useful hardware diagnostics, and a strong unit-test base. The next milestone should be reliable exhibition operation: reproducible startup, trustworthy connection state, failure-tolerant shutdown, preserved calibration, and recorded physical acceptance.

The existing architecture can support that work. A framework migration or broad rewrite would add risk before addressing the concrete defects below. Preserve the `Base` tree, driver boundaries, and focused test doubles while strengthening their lifecycle contracts.

The most important scope decision is whether the exhibition accepts emulated hearing and manually operated mirrors. Light-pattern search and reinforcement orchestration exist, but their presence does not establish a complete physical conversation between the mobiles.

## Review Scope and Verification

Reviewed Python startup, the object tree, command routing, persistence, logging, servo/Arduino boundaries, firmware responses, interaction behavior, tests, tooling, and hardware instructions. Three independent review passes covered runtime, hardware, and quality concerns; findings were checked against the source and targeted reproductions.

| Check | Result |
| --- | --- |
| Automated suite, Python 3.14.6 | **1,497 passed**, 28.48 seconds with coverage |
| Statement coverage, applying repository archive exclusions | **65.16%**, 9,539 / 14,640 statements |
| Scoped mypy | Passed: 11 source files |
| Ruff | Five minor findings: three unused imports and two unnecessary f-string prefixes |
| Failure reproductions | Confirmed logger startup/deletion/rotation, interrupted parameter save, POST lock bypass, rejected Arduino connection reuse, and skipped torque shutdown during motor removal |

Tests ran from a disposable directory with its own `local/logs`, because importing the current logger deletes that directory. The initial coverage report included archived code because coverage discovered configuration from the temporary working directory; applying the repository's configured exclusions to the same data corrected 53% to 65.16%. This is statement coverage, not branch or physical-behavior coverage.

The run used an existing development environment, not a clean dependency installation. No application server, hardware session, firmware upload, or physical movement was started. Repository calibration and logs were preserved. CAD and electronics were inspected through source and documentation; this review does not validate the circuit design or component ratings.

## Priority Findings

### 1. P1: Motor removal can skip torque shutdown after a homing failure

`Motors.unplug()` writes `plugged in=False`, then homes the installation, then disables torque. `move_to_origin()` catches errors while issuing goals, but its subsequent movement-status wait is outside that handler. A servo read failure therefore skips torque shutdown. The tree renders the failure as a recoverable command error, so the server's emergency-stop fallback is not invoked. A second removal attempt reports that the motors are already marked unplugged.

Evidence: [motor removal](../Source%20code/Python/colloquy/hardware/motors/__init__.py), lines 133-150; [homing and power-down](../Source%20code/Python/colloquy/__init__.py), lines 422-452; [command error handling](../Source%20code/Python/colloquy/ui/tree.py), lines 93-103. A double with an injected homing-read error confirmed that torque shutdown was never called. The ordinary `/shutdown` path has an emergency-stop fallback; the exposed motor-removal path is the stronger finding.

**Next:** make torque-disable attempts unconditional cleanup after failed homing, continue across individual servo failures, and report which outputs could not be confirmed off. Wait only on the servos that were commanded. Represent incomplete removal separately from completed removal and allow recovery.

**Acceptance:** injected goal-write, status-read, and individual torque-write failures cannot skip the remaining shutdown attempts; a failed removal remains visibly incomplete and retryable.

### 2. P1: Rejected Arduino firmware remains available for later commands

`Arduino.open()` opens the port before checking the board greeting. A rejected greeting leaves the handle open. Later `__enter__()` calls check only `is_open`, allowing commands on the connection whose firmware validation failed. Startup deliberately keeps the UI running after such failures, making this a reachable sequence.

Evidence: [Arduino connection lifecycle](../Source%20code/Python/colloquy/drivers/arduino/__init__.py), lines 106-113 and 298-308; [startup recovery](../main.py), around line 90. Extracted production methods with a fake port reproduced failed validation followed by a successful command write without another greeting check.

**Next:** distinguish an open serial handle from a validated, ready device. Close and invalidate on failed handshakes, port changes, and connection loss. Keep diagnostics and firmware recovery available while refusing ordinary commands.

**Acceptance:** an invalid or absent greeting prevents every subsequent command until a successful new handshake. Test that sequence on the same driver instance.

### 3. P1: Hardware instructions still contradict an actual amplifier failure

The incident report records an amplifier destroyed by a supply choice based on an unsupported rating. The later PCB section reopens that decision, but the rework instructions and introductory PCB text still describe it as settled. These documents are exposed through the application's hardware pages.

Evidence: [DIRTY_REWORK.md](../Source%20code/Python/colloquy/hardware/electronics/DIRTY_REWORK.md), lines 73-78 and 620-622; [NEXT_PCB.md](../Source%20code/Python/colloquy/hardware/electronics/NEXT_PCB.md), line 16 versus lines 371-393; [incident report](errors/2026-09-01-01.txt).

**Next:** reconcile all actionable instructions with the incident report immediately. Separate requirements for a future amplifier from verified properties of the modules already installed. Record component identity and authoritative rating evidence before choosing its supply or finalizing the corresponding PCB design. This review establishes no new electrical rating.

**Acceptance:** every operator-facing document agrees about the unresolved component choice, and every proposed supply limit has evidence for the actual selected part.

### 4. P1: Logging breaks fresh startup and destroys diagnostic evidence

[logger.py](../Source%20code/Python/colloquy/logger.py), lines 10-12, deletes `local/logs` during import, without checking whether it exists. A clean checkout fails before startup; an existing installation loses its previous logs merely by importing the package, including during test collection.

Rotation also discards the result of `lines[-1000:]` at line 55. Files keep growing and are repeatedly rewritten after the threshold. The rewrite drops the final newline, joining subsequent records. A disposable-directory reproduction confirmed the missing-directory failure, prior-log deletion, and merged records after 2,002 writes.

**Next:** initialize logging explicitly, retain prior sessions, and use bounded rotation with consistent encoding and shared synchronization. Avoid filesystem changes during module imports.

**Acceptance:** startup succeeds without a pre-existing `local/`; importing modules preserves files; rotation keeps complete records within the intended bound; concurrent writers remain readable.

### 5. P1: Interrupted parameter saves can destroy calibration

[Params](../Source%20code/Python/colloquy/params.py), lines 419-450, saves after each insertion and opens the authoritative JSON file with `"w"`. Construction also repeatedly saves partially assembled data, so loading existing calibration creates a write-failure window even without a user edit. There is no atomic replacement or writer lock.

A failed-write reproduction using a temporary calibration file left only `{` on disk. Existing version-migration backups are useful but do not cover every ordinary save.

**Next:** build and validate complete in-memory data before persisting. Serialize mutations and writes; write a temporary sibling, then replace the destination atomically. Retain a last-known-good version and a clear recovery path. Do not silently replace damaged calibration with defaults.

**Acceptance:** injected serialization and replacement failures preserve the previous readable calibration; migrations produce a complete document; simultaneous updates cannot corrupt it.

### 6. P1: POST edits bypass command locking and recoverable error handling

[WSGI2._parse_post](../Source%20code/Python/colloquy/server2/wsgi2.py), lines 200-216, resolves and calls a handler directly. GET commands instead pass through the application's command lock and `CommandFailed` handling. A reproduction confirmed that the POST handler runs with the lock unheld.

Edits can overlap commands or shutdown. An editor exception also reaches the server's emergency-stop handler instead of producing the normal recoverable error page. Malformed lengths, text encoding, or URL encoding similarly escape request parsing.

**Next:** route both methods through one command-execution boundary with locking and error translation. Validate and bound request input before dispatch, returning client errors for malformed input. Preserve the dedicated emergency-stop path's ability to interrupt a busy command.

**Acceptance:** controlled POST/GET/shutdown interleavings respect the same command policy; failed saves and malformed requests leave the control UI available; emergency stop remains independently reachable.

### 7. P2: Missing serial acknowledgements are reported as successful outputs

[Arduino._send_unsafe](../Source%20code/Python/colloquy/drivers/arduino/__init__.py), lines 240-253, accepts `b""` after a read timeout; its timeout exception is commented out. [AllAudio.silence](../Source%20code/Python/colloquy/drivers/all_audio/__init__.py), lines 98-107, subsequently marks every speaker silent. Other output callers also ignore or loosely interpret responses.

The [firmware](../Source%20code/Arduino/colloquy_of_mobiles/colloquy_of_mobiles.ino), around lines 672 and 718, sends a terminated response for commands. A valid blank response and receiving no bytes are distinguishable. A fake-port reproduction confirmed that no response raises no error.

**Next:** validate command-specific acknowledgements and represent unconfirmed output state honestly. Define recovery after timeouts, delayed replies, and board resets so the next command cannot consume a stale response.

**Acceptance:** missing, partial, malformed, and delayed responses never produce a confirmed-success state; recovery restores protocol alignment.

### 8. P2: Bootstrap and documentation lag behind the implementation

`requirements.txt` omits direct dependencies such as `matplotlib` and `numpy`; `pyserial` is directly used but may currently arrive transitively. Development requirements omit the documented mypy check and the watcher's `watchdog`. Versions are unconstrained, and no tracked CI workflow or supported-runtime declaration establishes a reproducible baseline.

The README's roadmap also describes completed work as missing: `Colloquy.close()` now collapses the UI node, female search runs pattern reading, and thread-error snapshots accept `focus_path`. Do not turn `close()` into process shutdown based on the old roadmap. Claims about approximately 200 tests, historical coverage, and no hardware use are outdated.

**Next:** declare direct dependencies and the supported interpreter, record a reproducible tested environment, and validate installation from an empty environment. Add pytest, Ruff, scoped mypy, and an isolated startup check to CI. Replace the old roadmap with dated milestones and distinguish implemented, emulated, physically tested, and unresolved behavior.

## Behavior Decision Required

[Hearing.is_emulated](../Source%20code/Python/colloquy/drivers/hearing/__init__.py), lines 65-72, always returns true. It reads the software state of singing bodies rather than decoding microphone measurements. This is explicitly documented and applies on the installation, too. [Mirrors](../Source%20code/Python/colloquy/drivers/mirror/__init__.py) currently expose calibration/manual movement rather than the complete reflected-light interaction.

Choose and document the exhibition target:

- **Current behavior accepted:** retain the substitution, make it visible to operators, and validate the complete installation against that specification.
- **Physical conversation required:** establish microphone channel mapping, signal/noise measurements, decoding reliability, and mechanical mirror limits first; then integrate a physical receiver behind the existing hearing boundary and add the intended mirror behavior.

This decision changes the feature scope substantially. Neither a passing simulator nor a successful speaker command proves that another body heard and decoded the message.

## Recommended Delivery Sequence

| Order | Work package | Completion evidence |
| --- | --- | --- |
| 1 | Reconcile amplifier instructions and define accepted exhibition behavior | One consistent hardware specification and an explicit decision about hearing/mirrors |
| 2 | Repair logging and clean bootstrap | Fresh environment can import/run checks; previous logs survive; declared dependencies suffice |
| 3 | Fix motor-removal cleanup, Arduino readiness, and acknowledgement handling | Fault-injection regressions for every failure sequence above |
| 4 | Make calibration saves recoverable and unify POST/GET command execution | Interrupted saves preserve calibration; concurrent/error requests preserve control |
| 5 | Establish automated release checks and rewrite the stale roadmap | Existing suite, new regressions, Ruff, scoped mypy, and isolated startup checks pass in CI |
| 6 | Conduct supervised installation acceptance, then a full opening-day-length soak | Recorded results tied to commit, firmware version, machine/ports, and calibration backup |
| 7 | Improve operator navigation and complete any newly required physical behaviors | Staff can start, diagnose, stop, and recover the agreed installation behavior |

Keep these as focused changes. Start software implementation with logging/bootstrap because it makes subsequent checks safe and reproducible; correct the hardware instructions in parallel. Resolve the operational P1 findings before unattended acceptance.

## Physical Acceptance and Remaining Investigation

Use existing hardware test pages and record expected versus observed results. Cover startup with a missing board or servo; stale firmware; a board reset or disconnected link; overlapping interactions; emergency stop during a long command; orderly shutdown and motor removal with a read failure; restart and schedule boundaries; and log/calibration survival across a full session. Electrical work requires the reconciled component specification first.

Automated tests should gain a separate isolated lifecycle harness, explicitly forced to virtual devices and temporary state. The unit suite's rule against constructing the real object graph is useful and should remain. Thread startup/registry synchronization, unbounded joins, and timeout recovery deserve focused follow-up experiments; they are investigation items, not additional reproduced defects in this report.

Prefer acceptance criteria around behavior and recovery over a blanket coverage target. The parameter module already has roughly 99% statement coverage while still allowing interrupted saves to destroy the file: executing a line does not test its failure contract.
