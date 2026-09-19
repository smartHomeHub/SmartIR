# Command regression tests

From the repository root, in a virtual environment:

```text
python -m pip install -r tests/requirements.txt
python -B -m unittest discover -s tests -v
```

The offline suite uses the standard library's `unittest` runner. It imports the
actual `climate.py` and `controller.py` modules with small Home Assistant boundary
substitutes in `support.py`. It executes the actual `Helper` class from
`__init__.py` for Pronto conversion without importing integration startup.
Synthetic codes are not appliance captures. No Home Assistant instance, network
service, credentials, or IR hardware is used.

The fake service registry distinguishes enqueueing from awaited handler completion.
Explicit gates exercise delayed sends, deferred failures and concurrent requests.
Tests also cover local preparation of the whole sequence before a preamble,
prepared payload snapshots, surfaced errors, cancellation, Off settings,
restoration and sensor callbacks. Invalid Hex or malformed JSON in a later
command must prevent all sends. Valid ESPHome scalar JSON is retained because
its registered service, not SmartIR, defines argument types.

Shared fan, light and media-player consumer tests exercise their actual source
methods. They record the existing optimistic state updates and error suppression;
they do not claim these platforms are transactionally state-safe. Awaiting a
surfaced error stops subsequent steps in a light's repeated-send loop.

## Pinned native Broadlink method contracts

The default offline suite skips these contracts unless
`SMARTIR_BROADLINK_SOURCE` names a separately obtained copy of
`homeassistant/components/broadlink/remote.py` from Home Assistant **2026.8.3**.
The test loader requires this SHA-256 before executing source:

```text
ff67b5280fdc8aaec99f1847abfe9c407d15486089a9db2555b676dd0e6ce8f6
```

Obtain the file explicitly from
https://raw.githubusercontent.com/home-assistant/core/2026.8.3/homeassistant/components/broadlink/remote.py
and set that environment variable before running the same unittest command.
Missing or mismatched source when the variable is set is an error, not a skip.
The tests do not download source automatically or vendor upstream code. The
upstream source remains under Home Assistant's Apache-2.0 license.

These contracts execute the pinned original method with isolated boundaries,
not a full Home Assistant instance. They cover an off remote's normal return,
swallowed device errors, surfaced extraction errors and successful completion.
They intentionally demonstrate that **handler completion can commit assumed
settings despite a known no-op or logged device error**. `blocking=True` cannot
recover an exception that the handler suppressed.

## Native Home Assistant interfaces

In a separate Linux virtual environment with Python **3.14.2 or newer**:

```text
python -m pip install -r tests/native_ha/requirements.txt
SMARTIR_NATIVE_HA=1 python -B -m unittest tests.native_ha.test_runtime -v
```

This separate suite uses native Home Assistant interfaces with no real network
or hardware. It does not qualify full integration startup or physical behavior.
SmartIR's package initializer still imports `distutils`, which is absent from
clean modern Python environments. The separate startup fix in
[SmartIR #1504](https://github.com/smartHomeHub/SmartIR/pull/1504) is not bundled
here. Loading platform code without that initializer must not be described as
an integration-startup test.

The workflow in `.github/workflows/tests.yml` runs both regression jobs on Linux.
The isolated job explicitly obtains hash-verified native-method source. The native
HA job uses the pinned HA release on Python 3.14.2. Pull-request workflow approval
may still be required by the upstream repository. Merely adding a workflow does
not establish that it passed.

The offline suite remains runnable on Python 3.13. Native HA 2026.8.3 tests cannot
run on that interpreter. Direct invalid-input tests do not establish that those
inputs pass HA service schemas, and no test establishes appliance acknowledgement.
