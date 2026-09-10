# FIELD//OS Performance Notes

## RVN-01 UI responsiveness

FIELD//OS must keep slow hardware probes off the Textual event loop.

Target behaviour:

- initial UI frame renders without waiting for GPS, mesh or network probes
- keyboard navigation remains responsive while telemetry is collected
- hardware telemetry is cached and refreshed asynchronously
- individual hardware checks may degrade or time out without blocking the operator interface

The Raspberry Pi 5 / RVN-01 target should feel immediate even when optional peripherals such as GPS are slow or unavailable.
