# Field Map (live — update while investigating)

| Offset | End | Length | Name | Type | Status | Confidence | Evidence |
|---:|---:|---:|---|---|---|---|---|
| 0x0000 | 0x0003 | 4 | magic | ASCII `SAVE` | Observed | High | constant in N samples |
| 0x0004 | 0x0005 | 2 | version | u16le | Inferred | Medium | values … |
| 0x0006 | 0x0007 | 2 | header_len | u16le → first payload off | Observed | High | points to 0x… |

Rules: one row per field/range; `Unknown` rows are mandatory, not embarrassing;
every Inferred+ needs the decisive test that would promote or kill it.
