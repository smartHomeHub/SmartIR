# Opt-in native boundary tests

There are two independent tiers. Neither contacts Home Assistant, a remote,
or an appliance. Normal `python -B -m unittest discover -s tests -v` skips both
tiers unless explicitly enabled. Missing opt-in means a reported skip, not a
passing native check. An explicitly selected missing file, mismatched source
hash, wrong HA version, or unsupported runtime is a failure.

## Pinned upstream Broadlink method, Python 3.13+

From the repository root, install `tests/requirements.txt` into a virtual
environment. Acquire the source with this **explicit network command**:

```text
python -B -m tests.native_ha.pinned_source .native-source/remote.py
```

Linux:

```sh
SMARTIR_BROADLINK_SOURCE=.native-source/remote.py python -B -m unittest tests.test_native_broadlink -v
```

PowerShell:

```powershell
$env:SMARTIR_BROADLINK_SOURCE = '.native-source\remote.py'
python -B -m unittest tests.test_native_broadlink -v
Remove-Item Env:SMARTIR_BROADLINK_SOURCE
```

The source URL is:
https://raw.githubusercontent.com/home-assistant/core/2026.8.3/homeassistant/components/broadlink/remote.py

The SHA256 is
`ff67b5280fdc8aaec99f1847abfe9c407d15486089a9db2555b676dd0e6ce8f6`.
The acquisition command and every test load verify the complete file before
executing anything. Do not commit the downloaded file. Remove `.native-source`
after testing. No upstream code is vendored by these tests. Upstream source is
Apache-2.0 licensed; see https://github.com/home-assistant/core/blob/2026.8.3/LICENSE.md
for its license and retain upstream notices if redistributing it.

Only the unchanged `BroadlinkRemote.async_send_command` method (lines 212-269)
is compiled, without its decorator. Unrelated learning methods use Python 3.14
syntax. The schema, `_extract_codes`, SDK exception class, device and storage
are explicit test substitutes. This does **not** validate native entity-service
schemas, Base64 extraction, native imports or hardware. Valid synthetic Base64
passes through the actual SmartIR climate/controller code. Extraction failure
is injected at the native method's extraction boundary.

Tests establish that an off remote and swallowed `BroadlinkException`/`OSError`
return normally, so SmartIR commits optimistic requested state. A surfaced
extraction error preserves prior state. Success waits for the device request.
Normal service completion is not evidence of appliance acknowledgement.

## Real Home Assistant runtime smoke, Linux Python 3.14.2+

Use a **separate environment/process**, not the isolated suite's HA substitutes.
The CI reference runtime is Linux Python **3.14.2**. Home Assistant is pinned to
**2026.8.3**; later versions must not silently stand in for it.

```sh
python --version
python -m pip install -r tests/native_ha/requirements.txt
SMARTIR_NATIVE_HA=1 python -B -m unittest tests.native_ha.test_runtime -v
```

This tier needs no downloaded Broadlink source and imports no `tests.support`
fixtures. It uses the installed HA `HomeAssistant`, `ServiceRegistry`,
`async_track_state_change_event`, and state machine with the actual SmartIR
climate/controller classes. Services are registered in memory, never forwarded
to a live remote. It covers blocking completion, surfaced service exceptions,
registry schema rejection, cancellation and lock release, real sensor-event
scheduling, and real state writes. A restore boundary test seeds the real HA
restore helper's in-memory cache and calls SmartIR's `async_added_to_hass` to
hydrate settings without sending. It does not test on-disk persistence.
The rejecting schema is synthetic, not HA's native remote service schema.

A package shell bypasses SmartIR's `__init__.py`, whose distutils/startup issue
is tracked separately in #1504. `Helper` is an unused placeholder for Base64
tests. Direct entities are intentionally not attached to an `EntityComponent`,
so their first state write emits HA's missing-platform warning. Sensor
callbacks are registered explicitly rather than via the restore lifecycle.
This is not full integration startup, discovery, restore persistence, entity-platform
or appliance validation. Test-owned config directories are created under the
repository and removed after shutdown.

Run the two commands separately in CI and require non-skipped results for
their respective opt-ins. Windows/Python 3.13 can validate the isolated pinned
method but cannot validate the native HA runtime tier.
