# Hardware Setup Guide

## Pin Configuration Reference

### Stepper Motor HAT Connections (BCM GPIO)

| Function | GPIO Pin | Physical Pin | Purpose |
|----------|----------|--------------|---------|
| Step | 17 | 11 | Pulse signal to motor driver |
| Direction | 27 | 13 | Forward/Backward control |
| Enable | 22 | 15 | Motor enable/disable |
| Limit Switch 1 | 23 | 16 | Home/Bottom limit |
| Limit Switch 2 | 24 | 18 | End/Top limit |

## Wiring Diagram

```
Raspberry Pi 3 B/B+ GPIO Header
┌─────────────────────────────┐
│ 1: 3.3V    │ 2: 5V         │
│ 3: GPIO2   │ 4: 5V         │
│ 5: GPIO3   │ 6: GND        │
│ 7: GPIO4   │ 8: GPIO14     │
│ 9: GND     │ 10: GPIO15    │
│11: GPIO17  ├─ STEP         │
│13: GPIO27  ├─ DIRECTION    │
│15: GPIO22  ├─ ENABLE       │
│16: GPIO23  ├─ LIMIT SW 1   │
│18: GPIO24  ├─ LIMIT SW 2   │
│19: GPIO10  │ 20: GND       │
│ ... remaining pins ...     │
└─────────────────────────────┘
```

## Component Connections

### Stepper Motor HAT
- **Step Pin (GPIO17)**: Connect to HAT PUL/STEP input
- **Direction Pin (GPIO27)**: Connect to HAT DIR input
- **Enable Pin (GPIO22)**: Connect to HAT EN input
- **GND**: Connect to HAT GND (shared with RPi)
- **5V Power**: Connect to HAT power input (external 5V supply)

### Stepper Motor
- Connect motor coils to HAT motor output terminals
- Typical NEMA 17: 4-wire or 6-wire configuration
- Refer to motor datasheet for exact wiring

### Limit Switches
- **Limit Switch 1** (GPIO23): End-of-travel sensor (normally open)
  - Connect one terminal to GPIO23
  - Connect other terminal to GND
  - Uses internal pull-up (active LOW)

- **Limit Switch 2** (GPIO24): End-of-travel sensor (normally open)
  - Connect one terminal to GPIO24
  - Connect other terminal to GND
  - Uses internal pull-up (active LOW)

## Power Supply

- **5V Supply**: 2-3A recommended for stepper motor HAT
- **Raspberry Pi**: 2A USB power (separate from motor supply, share GND)
- Connect GND from both supplies together

## Safety Considerations

1. **Disable motors** when adjusting mechanical components
2. **Test limit switches** before enabling AUTO_STOP_AT_LIMIT
3. **Use proper shielding** for motor power cables (can cause RF interference)
4. **Keep fingers clear** of moving parts during operation

## Testing Connection

1. Run system without motor connected:
   ```bash
   python3 stepper_controller.py
   ```

2. Check GPIO pin activity with:
   ```bash
   gpio readall
   ```

3. Verify limit switches trigger correctly during movement

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Motor not spinning | Check enable pin (GPIO22), verify power supply |
| Wrong direction | Swap direction pin connection or invert in config |
| Limit switch not detected | Check pin connection, verify pull-up resistance |
| Erratic movement | Check for loose connections, use shielded cables |
| GPIO permission denied | Run with sudo or add user to gpio group |

## GPIO Group Access (Optional)

To run without `sudo`:
```bash
sudo usermod -a -G gpio pi
```
Then log out and log back in.
