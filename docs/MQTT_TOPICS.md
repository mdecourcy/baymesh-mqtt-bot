# MQTT Topics & Payloads

## Topic Structure
Default root: `msh/US/bayarea`. The client subscribes to:
```
msh/US/bayarea/#
```

Common subtopics:
- `msh/US/bayarea/2/json`
- `msh/US/bayarea/2/protobuf`
- `msh/US/bayarea/telemetry`

## Payload Format
- Raw binary protobuf (`meshtastic.mesh_pb2.Data`).
- Fields of interest:
  - `id`, `from`, `to`
  - `rx_time` (unix epoch)
  - `rx_metadata` (RSSI, SNR per gateway)
  - `decoded.payload` or `decoded.text`

Example (decoded):
```json
{
  "id": 12345,
  "from": 0x12345678,
  "rx_time": 1700000000,
  "rx_metadata": [
    {"rssi": -90, "snr": 5.2, "from_ident": "GatewayA"},
    {"rssi": -95, "snr": 4.8, "from_ident": "GatewayB"}
  ],
  "decoded": {
    "text": "Hello mesh!"
  }
}
```

## Gateway Count Calculation
`ProtobufMessageParser.get_gateway_count()` counts entries in `rx_metadata`. If missing, defaults to 1 (direct).

## Adding Custom Topics
Update `.env` `MQTT_ROOT_TOPIC` and ensure permissions/ACLs allow subscription.



