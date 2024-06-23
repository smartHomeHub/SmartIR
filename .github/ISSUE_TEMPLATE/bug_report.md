---
name: Bug report
about: Create a report to help us improve
title: ''
labels: potential bug
assignees: litinoveweedle

---

**Disclaimer**
- Issues without a detailed, clear unambiguous description will be closed.
- Issues obviously related to not reading or not following documentation will be closed.
- Issues without debug logging will be closed.
- Issues without configuration will be closed.
- This is FOSS project, help yourself by helping others. The more invalid bugs will be opened the less time will be for the project maintenance.

**Search all existing issues**
Before you open a new issue, search through the existing issues to see if others have had the same problem. This includes not only open issues but issues already closed. If you think you issue is only related, but not same please refer to the given issue number. Confirm that you tried to search the issues including already closed ones.

**Home Assistant version**

**SmartIR version**

**SmartIR configuration**

```yaml

Add SmartIR relevant part of HA configuration.yaml  formatted as a code here

```

**Describe the bug**
A clear and concise description of what the bug is. This has to be as detailed as possible. 

**Expected behavior**
A clear and concise description of what you expected to happen.
 
**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. See error

**Debug log**
Enable integration debug logging, reproduce the bug and attached log. Insert log formatted as a code to keep it readable. To enable debug logging, put into your HA configuration.yaml following lines and restart HA.

```yaml
logger:
  default: warning
  logs:
    custom_components.smartir.climate: debug
```

**Additional context**
Add any other context about the problem here.
